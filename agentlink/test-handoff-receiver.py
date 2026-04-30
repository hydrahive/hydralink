#!/usr/bin/env python3
"""
AgentLink Handoff Receiver Test
Subscribe to agent:castiel channel and wait for handoff events
"""
import asyncio
import websockets
import json
from datetime import datetime

async def receive_handoffs():
    uri = "ws://192.168.178.102:8000/ws"
    
    print(f"[{datetime.now().isoformat()}] Connecting to {uri}...")
    
    try:
        async with websockets.connect(uri) as ws:
            print(f"[{datetime.now().isoformat()}] Connected!")
            
            # Wait for welcome message
            welcome = await ws.recv()
            print(f"[{datetime.now().isoformat()}] Welcome: {welcome}")
            
            # Subscribe to agent:castiel channel
            subscribe_msg = {"action": "subscribe", "channel": "agent:castiel"}
            await ws.send(json.dumps(subscribe_msg))
            print(f"[{datetime.now().isoformat()}] Sent: {subscribe_msg}")
            
            # Wait for subscription confirmation
            confirm = await ws.recv()
            print(f"[{datetime.now().isoformat()}] Subscription: {confirm}")
            
            print(f"\n{'='*60}")
            print("🎧 LISTENING FOR HANDOFFS...")
            print(f"{'='*60}\n")
            
            # Listen for messages
            async for message in ws:
                timestamp = datetime.now().isoformat()
                data = json.loads(message)
                
                print(f"[{timestamp}] Received:")
                print(json.dumps(data, indent=2))
                
                if data.get("type") == "handoff_received":
                    print(f"\n{'='*60}")
                    print("🎉 HANDOFF RECEIVED!")
                    print(f"From: {data.get('from_agent')}")
                    print(f"State ID: {data.get('state_id')}")
                    print(f"Reason: {data.get('reason')}")
                    print(f"{'='*60}\n")
    
    except Exception as e:
        print(f"[{datetime.now().isoformat()}] Error: {e}")

if __name__ == "__main__":
    asyncio.run(receive_handoffs())
