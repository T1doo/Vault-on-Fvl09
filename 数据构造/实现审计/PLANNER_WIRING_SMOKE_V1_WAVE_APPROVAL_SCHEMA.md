# Planner Wiring Smoke V1 Wave Approval Schema

Schema SHA：`71232608c1b8488f95d1ff198e353dd8199931dfc3441c8be507c9a06094db34`。

一份未来的wave approval必须同时绑定activation contract、152-query proposal、manifest bundle、ordered job slots、aggregate budget、conditional issuance rules、Vault HEAD、implementation source和RoboTwin tracked HEAD。通过后issuer仍逐job生成短期single-use authorization；不需要每个job再次人工批准。

本文件只定义schema，`approval_granted_by_schema=false`，没有创建或授予真实wave approval。
