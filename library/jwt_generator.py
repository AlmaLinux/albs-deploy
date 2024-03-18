#!/usr/bin/python
"""ALBS/ALTS JWT generation Ansible module."""
from __future__ import absolute_import, division, print_function  # noqa: WPS422

__metaclass__ = type

_DOCUMENTATION = """
---
module: ALBS JWT generator

short_description: JWT generator for ALBS and ALTS.

version_added: "1.0.0"

description:
    - This module provides a way to easily generate JWT tokens for both ALBS
      and ALTS. It depends on PyJWT.

options:
    target:
        description: Target system, either 'albs' or 'alts'.
        required: true
        type: str
        choices: [ albs, alts ]

    secret:
        description: Secret to use when generating the token.
        type: str
        required: true

    email:
        description: e-mail address to be included in the token.
        type: str

    user_id:
        description: ALBS user id.
        type: str

author:
    - Javier Hernández (@javihernandez)
"""

_EXAMPLES = """
- name: Create token for ALBS
  jwt:
    target: albs
    secret: secret
    user_id: 1

- name: Create token for ALTS
  jwt:
    target: alts
    secret: secret
    email: user@almalinux.org
"""

# ==============================================================

from ansible.module_utils.basic import AnsibleModule

import jwt

ALGORITHM="HS256"
FASTAPI_AUDIENCE=["fastapi-users:auth"]
EXPIRE_TIME=1777628461


def generate_jwt(payload, secret):
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def run_module():
    """
    Ansible module implementation.

    This is the function that Ansible calls when the module is invoked.
    """
    module_args = {
        'target': {
            'type': 'str',
            'choices': ['albs', 'alts'],
            'required': True,
        },
        'secret': {
            'type': 'str',
            'required': True,
        },
        'user_id': {
            'type': 'str',
        },
        'email': {
            'type': 'str',
        },
    }

    module_result = {
        'changed': False,
        'msg': '',
        'token': '',
    }

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
    )

    if module.check_mode:
        module.exit_json(**module_result)

    target = module.params['target']
    if not target:
        module.fail_json(msg="Missing required parameter 'target'")

    secret = module.params['secret']
    if not secret:
        module.fail_json(msg="Missing required parameter 'secret'")

    payload = {
        'exp': EXPIRE_TIME
    }

    if target == 'albs':
        user_id = module.params['user_id']
        if not user_id:
            module.fail_json(msg="Missing required paramenter 'user_id'")

        payload.update(
            {
                "sub": user_id,
                "aud": FASTAPI_AUDIENCE,
            }
        )
    else:
        email = module.params['email']
        if not email:
            module.fail_json("Missing required parameter 'email'")
        payload.update(
            {
                "email": email
            }
        )

    try:
        token = generate_jwt(payload, secret)
        module_result['msg'] = 'Successfully generated JWT token'
        module_result['token'] = token
    except Exception as err:
        module.fail_json(msg=str(err))

    module.exit_json(**module_result)


if __name__ == '__main__':
    run_module()
