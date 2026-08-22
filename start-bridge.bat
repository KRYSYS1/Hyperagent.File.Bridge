@echo off
REM ==================================================================
REM   Hyperagent Local File Bridge - autostart (supergateway + devtunnel)
REM   Edit the 3 values below, then double-click this file.
REM ==================================================================

REM Folder(s) the agent will access.
REM Single folder (no spaces in path) - just write it:
set "FOLDER=C:\hyperagent-bridge"
REM Several folders, or a path WITH SPACES - wrap EACH path in \" \" like this:
REM set "FOLDER=\"C:\projects\" \"E:\Games\My Game With Spaces\" \"D:\docs\""

REM Local port (do not change):
set "PORT=8008"

REM Your permanent tunnel ID from "devtunnel create" (e.g. abcd1234.eun1):
set "TUNNEL_ID=PUT-YOUR-TUNNEL-ID-HERE"

echo Starting supergateway (server) ...
start "MCP Bridge - server" cmd /k npx -y supergateway --stdio "npx -y @modelcontextprotocol/server-filesystem %FOLDER%" --port %PORT% --outputTransport streamableHttp

echo Waiting 6 seconds for the server to come up ...
timeout /t 6 >nul

echo Starting devtunnel (tunnel) ...
start "MCP Bridge - tunnel" cmd /k devtunnel host %TUNNEL_ID% --allow-anonymous

echo.
echo Bridge is starting in TWO windows: "server" and "tunnel".
echo Both must stay open. Closing a window = bridge OFF.
