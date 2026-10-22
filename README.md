# Prereqs

You need `uv`

# Startup

Its best if you use vscode and use the run and debug. A launch task is already created which I have described how to use in the video.

If you want to start the programs manually, use uv:

First export the seed variable

```bash
export SEED=1
```

For a router

```bash
uv run router --addr "Router A" --topology topology/upper.toml --network-conditions conditions/none.toml
uv run router --addr "Router B" --topology topology/upper.toml --network-conditions conditions/none.toml
uv run router --addr "Router C" --topology topology/upper.toml --network-conditions conditions/none.toml
uv run router --addr "Router D" --topology topology/upper.toml --network-conditions conditions/none.toml
```

You will probably need to run each command in different terminals or termux.

For a host

```bash
uv run host --addr "Host 1" --topology topology/upper.toml --network-conditions conditions/none.toml
uv run host --addr "Host 2" --topology topology/upper.toml --network-conditions conditions/none.toml
```

You cannot send input to a router. You can send a message from a host by sending a line "<destination address>:<message>"

# Core tests

For now since I dont have a good testing harness set up, the tests are ran as bash scripts inside of the acceptance_scenarios directory. If you want to read them they are fairly straightforward. They just set up the router and host processes, then send input to one of the host processes, then either logs are spit out or success/failure messages are counted.

You will need bash to run those, and you will need to be on Linux to run "error_handling.bash". If you do not have a linux environment, you can delete the line "printf '\xff\xfe\x00garbage' > /dev/udp/127.0.0.1/31217".

```bash
bash acceptance_scenarios/hop_limit.bash
```

# Configuration

Configuration is in the topology and conditions directories.