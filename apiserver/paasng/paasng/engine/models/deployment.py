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
import json
import logging
from pathlib import Path
from typing import Optional

from attrs import define
from bkpaas_auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext as _
from jsonfield import JSONField

from paasng.dev_resources.sourcectl.models import VersionInfo
from paasng.engine.constants import BuildStatus, ImagePullPolicy, JobStatus
from paasng.engine.controller.exceptions import BadResponse
from paasng.engine.controller.state import controller_client
from paasng.engine.exceptions import DeployInterruptionFailed
from paasng.engine.models.base import OperationVersionBase
from paasng.metrics import DEPLOYMENT_STATUS_COUNTER, DEPLOYMENT_TIME_CONSUME_HISTOGRAM
from paasng.platform.modules.models.deploy_config import HookList, HookListField
from paasng.utils.models import make_legacy_json_field

logger = logging.getLogger(__name__)


class DeploymentQuerySet(models.QuerySet):
    """Custom QuerySet for Deployment model"""

    def owned_by_module(self, module, environment=None):
        """Return deployments owned by module"""
        envs = module.get_envs(environment=environment)
        return self.filter(app_environment__in=envs)

    def latest_succeeded(self):
        """Return the latest succeeded deployment of queryset"""
        return self.filter(status=JobStatus.SUCCESSFUL.value).latest('created')


@define
class AdvancedOptions:
    dev_hours_spent: Optional[float] = None
    source_dir: str = ""
    image_pull_policy: ImagePullPolicy = ImagePullPolicy.IF_NOT_PRESENT


AdvancedOptionsField = make_legacy_json_field(cls_name="AdvancedOptionsField", py_model=AdvancedOptions)


class Deployment(OperationVersionBase):
    """部署记录"""

    app_environment = models.ForeignKey(
        'applications.ApplicationEnvironment', on_delete=models.CASCADE, related_name='deployments', null=True
    )
    status = models.CharField(u"部署状态", choices=JobStatus.get_choices(), max_length=16, default=JobStatus.PENDING.value)

    # Related with engine
    build_process_id = models.UUIDField(max_length=32, null=True)
    build_id = models.UUIDField(max_length=32, null=True)
    build_status = models.CharField(choices=BuildStatus.get_choices(), max_length=16, default=BuildStatus.PENDING)
    build_int_requested_at = models.DateTimeField(null=True, help_text='用户请求中断 build 的时间')
    pre_release_id = models.UUIDField(max_length=32, null=True)
    pre_release_status = models.CharField(
        choices=JobStatus.get_choices(), max_length=16, default=JobStatus.PENDING.value
    )
    pre_release_int_requested_at = models.DateTimeField(null=True, help_text='用户请求中断 pre-release 的时间')
    release_id = models.UUIDField(max_length=32, null=True)
    release_status = models.CharField(choices=JobStatus.get_choices(), max_length=16, default=JobStatus.PENDING.value)
    release_int_requested_at = models.DateTimeField(null=True, help_text='用户请求中断 release 的时间')

    err_detail = models.TextField(u"部署异常原因", null=True, blank=True)
    advanced_options: AdvancedOptions = AdvancedOptionsField("高级选项", null=True)

    procfile = JSONField(
        default=dict, help_text="启动命令, 在准备阶段 PaaS 会从源码(或配置)读取应用的 procfile, 并更新该字段, 在发布阶段将从该字段读取 procfile"
    )
    hooks: HookList = HookListField(help_text="部署钩子", default=list)

    objects = DeploymentQuerySet().as_manager()

    def __str__(self):
        return "{app_code}-{region}-{process}-{status}".format(
            app_code=self.get_application().code,
            region=self.get_application().region,
            process=self.build_process_id,
            status=self.status,
        )

    def update_fields(self, **u_fields):
        logger.info('update_fields, deployment_id: {} , fields: {}'.format(self.id, json.dumps(u_fields)))
        before_time = self.updated
        kind: Optional[str]
        status: Optional[str]
        if 'release_status' in u_fields:
            kind = 'release'
            status = JobStatus(u_fields['release_status'])
        elif 'build_status' in u_fields:
            kind = 'build'
            status = JobStatus(u_fields['build_status'])
        else:
            kind = None
            status = None
        for key, value in u_fields.items():
            setattr(self, key, value)
        self.save()

        if kind and status in JobStatus.get_finished_states():
            DEPLOYMENT_STATUS_COUNTER.labels(kind=kind, status=status.value).inc()
            total_seconds = (self.updated - before_time).total_seconds()
            logger.info(f'update_release {total_seconds}')
            DEPLOYMENT_TIME_CONSUME_HISTOGRAM.labels(
                language=self.app_environment.application.language, kind=kind, status=status.value
            ).observe(total_seconds)

    def get_engine_app(self):
        return self.app_environment.get_engine_app()

    def get_application(self):
        return self.app_environment.application

    def fail_with_error(self, err_detail, status=None):
        self.update_fields(err_detail=err_detail, status=status or self.status)

    def get_source_dir(self) -> Path:
        """获取源码目录"""
        if not self.advanced_options:
            return Path(".")
        path = Path(self.advanced_options.source_dir)
        if path.is_absolute():
            logger.warning("Unsupported absolute path<%s>, force transform to relative_to path.", path)
            path = path.relative_to("/")
        return path

    @property
    def logs(self):
        logs_ = []
        if self.build_process_id:
            from paasng.engine.deploy.engine_svc import EngineDeployClient

            lines = EngineDeployClient(self.get_engine_app()).list_build_proc_logs(self.build_process_id)
            for item in lines:
                logs_.append(item["line"].replace('\x1b[1G', ''))

        if self.pre_release_id:
            resp = controller_client.command__retrieve(
                region=self.region, app_name=self.get_engine_app().name, command_id=self.pre_release_id
            )
            for item in resp["lines"]:
                logs_.append(item["line"].replace('\x1b[1G', ''))

        return "".join(logs_) + "\n" + (self.err_detail or '')

    def has_succeeded(self):
        return self.status == JobStatus.SUCCESSFUL.value

    @property
    def has_requested_int(self) -> bool:
        """If an interruption request has been made"""
        return bool(self.build_int_requested_at or self.release_int_requested_at)

    @property
    def start_time(self) -> Optional[str]:
        """获取部署阶段开始时间"""
        # Deployment 肯定是以 PREPARATION 开始
        from paasng.engine.models.phases import DeployPhaseTypes

        try:
            return self.deployphase_set.get(type=DeployPhaseTypes.PREPARATION.value).start_time
        except Exception:
            # 防御，避免绑定阶段中访问此 API 异常
            logger.warning("failed to get PREPARATION start time from deployment<%s>", self.pk)
            return None

    @property
    def complete_time(self) -> Optional[str]:
        """获取部署阶段结束时间"""
        # 但是可能以任意状态结束
        try:
            return (
                self.deployphase_set.filter(status__in=JobStatus.get_finished_states())
                .order_by("-complete_time")
                .first()
                .complete_time
            )
        except Exception:
            logger.warning("failed to get complete status from deployment<%s>", self.pk)
            return None

    @property
    def finished_status(self) -> Optional[str]:
        """获取最后结束的阶段状态"""
        try:
            return (
                self.deployphase_set.filter(status__in=JobStatus.get_finished_states())
                .order_by("-complete_time")
                .first()
                .type
            )
        except Exception:
            logger.warning("failed to get complete status from deployment<%s>", self.pk)
            return None

    @property
    def version_info(self):
        return VersionInfo(self.source_revision, self.source_version_name, self.source_version_type)

    def get_deploy_hooks(self) -> HookList:
        try:
            hooks = self.declarative_config.get_deploy_hooks()
        except Exception:
            hooks = HookList()

        for hook in self.hooks:
            if hook.enabled:
                hooks.upsert(hook.type, hook.command)
        return hooks


def interrupt_deployment(deployment: Deployment, user: User):
    """Interrupt a deployment, this method does not guarantee that the deployment will be interrupted
    immediately(or in a few seconds). It will try to do following things:

    - When in "build" phase: this method will try to stop the build process by calling engine service
    - When in "release" phase: this method will set a flag value and abort the polling process of
      current release

    After finished doing above things, the deployment process MIGHT be stopped if anything goes OK, while
    the interruption may have no effects at all if the deployment was not in the right status.

    :param deployment: Deployment object to interrupt
    :param user: User who invoked interruption
    :raises: DeployInterruptionFailed
    """
    if deployment.operator != user.pk:
        raise DeployInterruptionFailed(_('无法中断由他人发起的部署'))
    if deployment.status in JobStatus.get_finished_states():
        raise DeployInterruptionFailed(_('无法中断，部署已处于结束状态'))

    now = timezone.now()
    deployment.build_int_requested_at = now
    deployment.release_int_requested_at = now
    deployment.save(update_fields=['build_int_requested_at', 'release_int_requested_at', 'updated'])

    if deployment.build_process_id:
        engine_app = deployment.get_engine_app()
        try:
            controller_client.interrupt_build_process(engine_app.region, engine_app.name, deployment.build_process_id)
        except BadResponse as e:
            # This error code means that build has not been started yet
            if e.get_error_code() == 'INTERRUPTION_NOT_ALLOWED':
                raise DeployInterruptionFailed(e.get_error_message())
            # Ignore other BadResponse errors
