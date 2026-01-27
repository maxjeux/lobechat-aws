# Fix: Add session retry logic to `callTool` (fixes #10455)

## Problem

`MCPService.callTool()` fails when the MCP server session is stale or terminated because it doesn't implement retry logic with session reinitialization.

**Error messages observed:**
- `"Bad Request: No valid session ID provided"`
- `"Bad Request: Server not initialized"`

## Root Cause

`listTools()` already has retry logic that works correctly:

```typescript
// src/server/services/mcp/index.ts - listTools (WORKS ✓)
async listTools(params, { retryTime, skipCache } = {}) {
  const client = await this.getClient(params, skipCache);
  try {
    const result = await client.listTools();
    return result.map(...);
  } catch (error) {
    if (error.message === 'NoValidSessionId' && retryTime <= 3) {
      return this.listTools(params, {
        retryTime: (retryTime || 0) + 1,
        skipCache: true  // ← Forces new session
      });
    }
    throw error;
  }
}
```

But `callTool()` is missing this same pattern:

```typescript
// src/server/services/mcp/index.ts - callTool (BROKEN ✗)
async callTool(options) {
  const client = await this.getClient(clientParams);  // ← No skipCache option
  const result = await client.callTool(toolName, args);
  // ← No retry on session errors
}
```

## Network Trace Evidence

Using `tcpflow` to capture traffic between LobeChat and MCPHub:

```http
POST /mcp/ssh-exec HTTP/1.1
mcp-session-id: 5ffaee42-d6ec-4f81-842a-0626c80f6239
content-type: application/json

{"method":"tools/call","params":{"name":"ssh-exec-ssh_exec",...},"jsonrpc":"2.0","id":10}
```

Response:
```http
HTTP/1.1 400 Bad Request
{"jsonrpc":"2.0","error":{"code":-32000,"message":"Bad Request: Server not initialized"},"id":null}
```

LobeChat sends a stale `mcp-session-id` and jumps directly to `tools/call` without reinitializing the session.

## Proposed Fix

Add the same retry pattern from `listTools()` to `callTool()`:

```typescript
async callTool(
  options: {
    argsStr: any;
    clientParams: MCPClientParams;
    processContentBlocks?: ProcessContentBlocksFn;
    toolName: string;
  },
  { retryTime = 0, skipCache = false } = {}
): Promise<any> {
  const { clientParams, toolName, argsStr, processContentBlocks } = options;
  const client = await this.getClient(clientParams, skipCache);
  const args = safeParseJSON(argsStr);
  const loggableParams = this.sanitizeForLogging(clientParams);

  try {
    const result = await client.callTool(toolName, args);
    return MCPService.processToolCallResult(result, processContentBlocks);
  } catch (error) {
    // Retry on session-related errors (same pattern as listTools)
    const errMsg = (error as Error).message || '';
    const isSessionError =
      errMsg === 'NoValidSessionId' ||
      errMsg.includes('No valid session ID') ||
      errMsg.includes('Server not initialized');

    if (isSessionError && retryTime <= 3) {
      console.log(
        `Session error calling tool "${toolName}", retrying (attempt ${retryTime + 1}/3)...`
      );
      return this.callTool(options, {
        retryTime: retryTime + 1,
        skipCache: true,
      });
    }

    if (error instanceof McpError) {
      return {
        content: error.message,
        error,
        state: { content: [{ text: error.message, type: 'text' }], isError: true },
        success: false,
      };
    }

    console.error(`Error calling tool "${toolName}" for params %O:`, loggableParams, error);
    throw new TRPCError({
      cause: error,
      code: 'INTERNAL_SERVER_ERROR',
      message: `Error calling tool "${toolName}" on MCP server: ${errMsg}`,
    });
  }
}
```

## Testing

### Before fix:
1. Configure MCP server in LobeChat
2. Use MCP tool successfully
3. Wait for session to expire or restart MCP server
4. Try to use MCP tool again → **Fails with 400 error**

### After fix:
1. Same steps as above
2. Try to use MCP tool again → **Automatically retries with fresh session** ✓

## Checklist

- [x] Follows existing code patterns (`listTools` retry logic)
- [x] Handles multiple error message formats
- [x] Limits retries to prevent infinite loops
- [x] Adds logging for debugging
- [x] Backward compatible (new parameters have defaults)
