# smoke

元 skill 冷启动验收（不含正文）。

```bash
cd 05-shi-shi-qiu-shi
https_proxy=http://127.0.0.1:7890 python3 scripts/run_coldstart.py
```

期望：空库 0 命中；临时目录能抓取实践论+孙子并检索命中；本机 `corpus/` 不被改写。
