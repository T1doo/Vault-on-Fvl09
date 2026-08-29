# runtime-v3_3 CPU baseline v1.5 publication receipt

内容提交已发布到Vault `main`：

```text
424b58ece2e43caf95e12e829431d825809281d9
```

绑定状态：

- active/snapshot source SHA=`40e2ef209ba407e44cdf952637d4725b57daa8194f9cde0cd7ab6d6b2cfaf037`；
- active/snapshot各256/256 tests passed，source/tests byte-equal；
- official tracked commit=`c3ddfa8b97d5519efa828b075999bd0006778e5e`且tracked clean；
- GPU0–7 budget v1.1 hash=`68cee0949ccb6d87bef5255560bf32737d0d79dc803dfd92ac71d1098cad5d2c`；
- F1 revision-1 evidence tree=`97c5be7fde97ffd3e22d5b06188f710a3b7b80f637da9a573e883fbd0ba137a0`；
- Stage 0/Stage 1/formal/training仍为0且未授权。

本receipt只证明CPU baseline已发布；不等于任何新GPU scope已签发或运行。下一步必须在本closeout commit也push、Vault clean且HEAD=origin/main后，才能由bundle builder生成fresh one-shot authorizations。
