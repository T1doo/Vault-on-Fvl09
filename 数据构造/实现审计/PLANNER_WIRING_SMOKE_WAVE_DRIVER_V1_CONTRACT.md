# Planner Wiring Smoke Wave Driver V1 Contract

Contract payload SHA：`4c88fd1fdb3767849a82469fb8e4caf8c9a61f8f4799fd75aca0536c2b26feff`。

Wave driver 只接受经过磁盘 schema/self-hash/file-SHA/authorization/outer/Guard 交叉验证的 prior terminal。每个 issuance、terminal、skip、registry、closure 与 final wave terminal 均 O_EXCL。Aggregate 上限为 152 queries、9 scenes、16200 seconds、0 physical、0 trajectory；任一 infrastructure error 永久关闭 wave。

本 contract 只封存实现，未创建 operational wave approval。
