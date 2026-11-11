# Phase 4 -- MCPpppppppppp!

## Things to know about how machines talk to machines -- the initialize phase
The required shape has two layers:

The JSON-RPC envelope, which is the same for every message.
A request has *jsonrpc, id, method, and params*.
A reply has *jsonrpc, the same id, and either result or error*.
A notification has *jsonrpc and method* but no id.
The MCP contents, where the MCP spec defines what goes in params and result for each method. For initialize, the spec requires protocolVersion, capabilities and clientInfo in the request, and protocolVersion, capabilities and serverInfo in the reply. They’re required even when they’re empty.

For my first session, here are the first 3 lines:
    init_request = '''{"jsonrpc": "2.0", "id": 4, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "git-bash-test", "version": "0.1"}}}'''

    init_reply = '''{"jsonrpc": "2.0", "id": 4, "result": {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}}, "serverInfo": {"name": "fde-sql", "version": "0.1"}}}'''

    initialized_note = '''{"jsonrpc": "2.0", "method": "notifications/initialized"}'''

It's saying hey I'm a client coming at ya from jsonrpc 2.0 and MCP version 2025/6/18, my name's git-bash-test and i'm version 1.0. This is question id 4 Come on?
Server says hey git-bash-test v1.0, I got ya on jsonrpc 2.0 and I will allow you to use MCP version 2025/6/18, and this is my response to question id 4. My names fde-sql version 1.0. I have some tools but I'm leaving that empty so you can request some tools.
Claude was a bit more pithy:
Client: “Here’s who I am and what version I propose.” (request)
Server: “Agreed, and here’s who I am and what I offer.” (reply)
Client: “Got it. We’re set.” (notification)

stdin is the channel every running program has
Every program gets three channels when it starts:
1. stdin
2. stdout
3. stderr

Channel	Direction	In a terminal it’s connected to	In Python
stdin	in	        your keyboard	input(), sys.stdin
stdout	out	        your screen	print()
stderr	out	        your screen too	print(..., file=sys.stderr)
