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
import random
from typing import Dict, Optional

from bkpaas_auth.models import User
from django.conf import settings
from django.utils.crypto import get_random_string

from paas_wl.platform.applications.models.app import EngineApp
from paas_wl.platform.applications.models.config import Config
from tests.utils.auth import create_user


def random_fake_app(
    force_app_info: Optional[Dict] = None,
    paas_app_code: Optional[str] = None,
    environment: Optional[str] = None,
    owner: Optional[User] = None,
) -> EngineApp:
    default_environment = random.choice(["stag", "prod"])
    default_app_name = 'app-' + get_random_string(length=12).lower()
    app_info = {
        "region": settings.FOR_TESTS_DEFAULT_REGION,
        "name": default_app_name,
        "structure": {"web": 1, "worker": 1},
        "owner": str(owner or create_user(username="somebody")),
    }

    if force_app_info:
        app_info.update(force_app_info)

    fake_app = EngineApp.objects.create(**app_info)
    # Set up metadata
    Config.objects.create(
        app=fake_app,
        metadata={
            "environment": environment or default_environment,
            # Use app name as paas_app_code by default if not given
            "paas_app_code": paas_app_code or app_info['name'],
            "module_name": 'default',
        },
    )
    return fake_app
