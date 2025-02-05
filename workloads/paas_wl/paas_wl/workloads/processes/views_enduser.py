# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
import datetime
import json
import logging
from typing import Dict, Optional

from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paas_wl.cnative.specs.procs import get_proc_specs
from paas_wl.platform.applications.constants import AppOperationType, EngineAppType
from paas_wl.platform.applications.models import EngineApp
from paas_wl.platform.applications.permissions import AppAction, application_perm_class
from paas_wl.platform.applications.views import ApplicationCodeInPathMixin
from paas_wl.platform.auth.views import BaseEndUserViewSet
from paas_wl.platform.external.client import get_plat_client
from paas_wl.platform.external.exceptions import PlatClientRequestError
from paas_wl.platform.system_api.serializers import ProcExtraInfoSLZ, ProcSpecsSerializer
from paas_wl.utils.error_codes import error_codes
from paas_wl.utils.views import IgnoreClientContentNegotiation
from paas_wl.workloads.processes.constants import ProcessUpdateType
from paas_wl.workloads.processes.controllers import get_proc_mgr, judge_operation_frequent
from paas_wl.workloads.processes.drf_serializers import (
    CNativeProcSpecSLZ,
    InstanceForDisplaySLZ,
    ListProcessesSLZ,
    ProcessSpecSLZ,
    UpdateProcessSLZ,
    WatchProcessesSLZ,
)
from paas_wl.workloads.processes.exceptions import ProcessNotFound, ProcessOperationTooOften, ScaleProcessError
from paas_wl.workloads.processes.managers import AppProcessManager
from paas_wl.workloads.processes.models import Instance, ProcessSpec
from paas_wl.workloads.processes.readers import instance_kmodel, process_kmodel
from paas_wl.workloads.processes.watch import watch_process_events

logger = logging.getLogger(__name__)


class ProcessesViewSet(BaseEndUserViewSet, ApplicationCodeInPathMixin):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    _operation_interval: datetime.timedelta = datetime.timedelta(seconds=3)
    _skip_judge_frequent: bool = False

    def update(self, request, code, module_name, environment):
        """操作进程，支持的操作：启动、停止、调整实例数"""
        slz = UpdateProcessSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        data = slz.validated_data

        module_env = self.get_module_env_via_path()
        if module_env.is_offlined:
            logger.warning("Unable to update process, environment %s has gone offline.", module_env)
            raise error_codes.CANNOT_OPERATE_PROCESS.f('环境已下架')

        engine_app = self.get_engine_app_via_path()
        process_type = data["process_type"]
        operate_type = data["operate_type"]
        target_replicas = data.get("target_replicas")
        try:
            judge_operation_frequent(engine_app, process_type, self._operation_interval)
        except ProcessOperationTooOften as e:
            raise error_codes.PROCESS_OPERATION_TOO_OFTEN.f(str(e), replace=True)

        self._perform_update(module_env, operate_type, process_type, target_replicas)

        # Create application operation log
        op_type = self.get_logging_operate_type(operate_type)
        if op_type:
            try:
                module = self.get_module_via_path()
                get_plat_client().create_operation_log(
                    application_id=str(module.application_id),
                    operate_type=op_type,
                    operator=request.user.pk,
                    source_object_id=str(module_env.id),
                    module_name=module.name,
                    extra_values={"process_type": process_type, "env_name": module_env.environment},
                )
            except PlatClientRequestError:
                logger.exception('Error creating app operation log')

        return Response(status=status.HTTP_204_NO_CONTENT)

    @staticmethod
    def get_logging_operate_type(type_: str) -> Optional[int]:
        """Get the type of application operation"""
        return {'start': AppOperationType.PROCESS_START, 'stop': AppOperationType.PROCESS_STOP}.get(type_, None)

    def _perform_update(self, module_env, operate_type: str, process_type: str, target_replicas: Optional[int] = None):
        ctl = get_proc_mgr(module_env)
        try:
            if operate_type == ProcessUpdateType.SCALE:
                assert target_replicas
                ctl.scale(process_type, target_replicas)
            elif operate_type == ProcessUpdateType.STOP:
                ctl.stop(process_type)
            elif operate_type == ProcessUpdateType.START:
                ctl.start(process_type)
            else:
                raise error_codes.PROCESS_OPERATE_FAILED.f(f"Invalid operate type {operate_type}")
        except ProcessNotFound as e:
            raise error_codes.PROCESS_OPERATE_FAILED.f(f"进程 '{process_type}' 未定义") from e
        except ScaleProcessError as e:
            raise error_codes.PROCESS_OPERATE_FAILED.f(str(e), replace=True)


class ListAndWatchProcsViewSet(BaseEndUserViewSet, ApplicationCodeInPathMixin):

    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    # Use special negotiation class to accept "text/event-stream" content type
    content_negotiation_class = IgnoreClientContentNegotiation

    def list(self, request, code, module_name, environment):
        """获取当前进程与进程实例，支持通过 release_id 参数过滤结果"""
        env = self.get_module_env_via_path()
        engine_app = self.get_engine_app_via_path()
        serializer = ListProcessesSLZ(data=request.query_params, context={'engine_app': engine_app})
        serializer.is_valid(raise_exception=True)

        data = get_proc_insts(engine_app, release_id=serializer.validated_data['release_id'])

        # For default apps: Attach ProcessSpec related data
        packages = ProcessSpec.objects.filter(engine_app=engine_app).select_related('plan')
        data['process_packages'] = ProcessSpecSLZ(packages, many=True).data

        # For cloud-native apps: Attach ProcessSpec-like data which have less
        # properties, it's useful for the client when implementing process actions
        data['cnative_proc_specs'] = CNativeProcSpecSLZ(get_proc_specs(env), many=True).data
        return Response(data)

    def watch(self, request, code, module_name, environment):
        """实时监听进程与进程实例变动情况"""
        engine_app = self.get_engine_app_via_path()
        serializer = WatchProcessesSLZ(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        def resp():
            logger.debug('Start watching process, app=%s, params=%s', engine_app.name, dict(data))
            stream = watch_process_events(
                engine_app,
                timeout_seconds=data['timeout_seconds'],
                rv_proc=data['rv_proc'],
                rv_inst=data['rv_inst'],
            )
            for event in stream:
                event = self.process_event(engine_app, event)
                yield 'event: message\n'
                yield 'data: {}\n\n'.format(json.dumps(event))

            yield 'id: -1\n'
            yield 'event: EOF\n'
            yield 'data: \n\n'
            logger.info('Watching finished, app=%s, params=%s', engine_app.name, dict(data))

        return StreamingHttpResponse(resp(), content_type='text/event-stream')

    @staticmethod
    def process_event(engine_app: EngineApp, event: Dict) -> Dict:
        """Process event payload, modifies original event"""
        payload = event['object']
        # Replace instance events with fewer fields
        if event['object_type'] == 'instance':
            event['object'] = InstanceForDisplaySLZ(Instance(app=engine_app, **payload)).data
        return event


def get_proc_insts(engine_app: EngineApp, release_id: Optional[str] = None) -> Dict:
    """Build a structured data including processes and instances

    :param release_id: if given, include instances created by given release only
    :return: A dict with "processes" and "instances"
    """
    procs = process_kmodel.list_by_app_with_meta(app=engine_app)
    procs_items = ProcSpecsSerializer(procs.items, many=True)

    insts = instance_kmodel.list_by_app_with_meta(app=engine_app)
    insts_items = InstanceForDisplaySLZ(insts.items, many=True)

    # Filter instances if required
    insts_data = insts_items.data
    if release_id:
        release = engine_app.release_set.get(pk=release_id)
        insts_data = [inst for inst in insts_data if inst['version'] == str(release.version)]

    # Get extra infos
    proc_extra_infos = []
    if engine_app.type != EngineAppType.CLOUD_NATIVE:
        for proc_spec in procs.items:
            release = engine_app.release_set.get(version=proc_spec.version)
            process_obj = AppProcessManager(app=engine_app).assemble_process(proc_spec.name, release=release)
            proc_extra_infos.append(ProcExtraInfoSLZ(process_obj).data)

    return {
        'processes': {
            'items': procs_items.data,
            'extra_infos': proc_extra_infos,
            'metadata': {'resource_version': procs.get_resource_version()},
        },
        'instances': {
            'items': insts_data,
            'metadata': {'resource_version': insts.get_resource_version()},
        },
    }
