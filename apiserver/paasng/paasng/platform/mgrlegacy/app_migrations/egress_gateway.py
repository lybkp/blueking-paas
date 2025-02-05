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
import logging

from django.utils.translation import gettext_lazy as _

from paasng.engine.controller.exceptions import BadResponse
from paasng.engine.controller.state import controller_client

from .base import BaseMigration

logger = logging.getLogger(__name__)


class EgressGatewayMigration(BaseMigration):
    """A Migration Process To enable app egress gateway"""

    def migrate(self):
        # 创建 Egress 记录
        application = self.context.app
        module = application.get_default_module()
        for env in module.get_envs():
            engine_app = env.engine_app
            try:
                controller_client.app_rcsbinding__create(engine_app.region, engine_app.name)
            except BadResponse as e:
                self.add_log(
                    _("{env} 环境绑定出口IP异常, 详情: {detail}").format(env=env.environment, detail=e.get_error_message())
                )

    def rollback(self):
        # 删除 Egress 记录
        application = self.context.app
        module = application.get_default_module()
        for env in module.get_envs():
            engine_app = env.engine_app
            try:
                controller_client.app_rcsbinding__destroy(engine_app.region, engine_app.name)
            except BadResponse as e:
                if e.status_code == 404:
                    self.add_log(_("{env} 环境未获取过网关信息").format(env=env.environment))
                else:
                    self.add_log(
                        _("{env} 环境解绑出口IP异常, 详情: {detail}").format(env=env.environment, detail=e.get_error_message())
                    )

    def get_description(self):
        return _("绑定出口 IP ")
