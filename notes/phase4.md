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

## My guess as to what the Python SDK will do for me inside the loop
I hope that it's going to wire up the transition from JSON to Python. That is going to let me just call the SQL server, specify the server, the tables, and the query, and it's going to take care of translating that into the call that the MCP server really needs. 

## 11/11 We built the SDK handshake. This is the "initialized" from the client, the response that it's initialized from the server, and then an unanswered "yes." I got your initialization response going back from the client to the server. 
We learned that there are two different kinds of errors. We needed to encapsulate a SQL Server error because the SQL Server error that the table doesn't exist actually proves that everything except SQL Server worked. We needed to raise that error and grab the text that SQL Server is sending back so the model would realize that everything about the SDK for MCP worked, but it needs to find a better SQL query. This was done using a ToolError. 
The SDK is asynchronous, meaning you have to call a flush command to get the things that you're sending over to go through. Flush just tells it to do everything that you've been waiting for, however long it takes. I think that's legacy functionality where it would wait for lots and lots of requests to pile up and then do them all at once. In this case, I don't want it to act like that, so I have to call some sort of a flush command.

Also, when I sent four different statements to it (the initialize statements and then the second client, which is responding, saying, "Yes, I understand that you responded to me," and then two requests), I had to wait 10 seconds to get that to work. When we waited 3 seconds, it didn't work. When we waited 10 seconds, it did. 


## 11/12 we modified a few functions so that MCP SDK could import them. This is because there were two statements in search_hybrid.py that were not inside any function. We needed to put them into the main function to protect them from being run at the time that the module is imported. Critically, one of them was a print statement, and that print statement would have messed up the MCP server's stdout and corrupted the protocol that it has in place for very structured communications. 
At the end of all that, we reran eval.py to make sure that we hadn't broken anything and, frankly, to check if anything had been improved. It was exactly the same as it was before. 

## 11/13
Now that the MCP server is set up in Claude Desktop, I can query the FIA corpus in Claude Desktop. We have shown that the model made at least one call. We were looking at the debugging information that the Claude Desktop app logs, which isn't really very human-readable. 

Made a decision that logging is not going to be part of the POC, but that we will have to put a log line in every call to the MCP server and a log line in every call to the agent. The MCP server log line is going to track who asked for what, and the agent is going to track what's in the messages list. 

The Claude model did something without me asking it to. That was kind of cool, and I didn't even know that it would do it. It changed my question, "What does AC 400343-203B cover?" into "Purpose of AC 43-203B," which made what it sent semantically a lot closer to what the answers were. It got the right answer as a result. 

Also, the model filtered on the correct PDF document. It's in a file source of 71398.pdf. 

In order to turn on the MCP server, we had to modify a file called claude_desktop_config.json, adding json to let it Note that there's an MCP server here, and the MCP server is called FDE Lab. Somehow I copied the word Git into that file as well. The weird thing is that I restarted Claude Desktop, and it went fine. Today I restarted Claude Desktop, and it said I didn't have any MCP servers.

Anyway, luckily I had saved a copy of it. The thing that I screwed up was very small. I was able to just modify it, but the lesson here is to be very, very careful with configuration files, obviously. 

Desktop made 2 calls: broad (keywords, no filter) → narrow (answer-shaped query + source_file learned from call 1). Works only because the tool returns source_file. The model never sends the user’s wording. Server-side stderr print was the only way to see this; the client log hides arguments.

Web chat reaches fde-lab only through the Desktop app on my laptop. Quit Desktop → tool gone. A local server is single-user and tied to one machine being on; shared access needs a remote server.

What test_sdk.jsonl is doing is acting like the client, sending several statements to the server In the proper format. It's a good test because it doesn't need the model. It doesn't need any of the other Python code other than MCP server SDK, and it just checks to make sure that that's working. 
That test is a great one for production runs when we've made code changes, right? If there's a code change to the MCP server, we want to identify whether the MCP server is working properly or not before we even get into whether the model is working. 
Here's how you run the piped test:
(cat test_sdk.jsonl; sleep 20) | python mcp_server_sdk.py

