"""Quick WebSocket smoke test for the chat endpoint."""
import asyncio
import json
import sys

import httpx
import websockets


async def test_websocket():
    """Test WebSocket chat end-to-end: connect → send → receive streaming response."""
    # 1. Get a fresh token
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "http://localhost:8000/api/v1/auth/login",
            json={"email": "test@fashionai.com", "password": "TestPass123!"},
        )
        if resp.status_code != 200:
            print(f"FAIL: Login returned {resp.status_code}: {resp.text}")
            return False
        token = resp.json()["access_token"]
        print(f"1. Login OK - token: {token[:30]}...")

    # 2. Connect via WebSocket
    ws_url = f"ws://localhost:8000/api/v1/chat/ws/test-session?token={token}"
    print(f"2. Connecting to WebSocket...")

    try:
        async with websockets.connect(ws_url, open_timeout=10) as ws:
            print("   Connected!")

            # 3. Send a message
            message = {
                "type": "message",
                "content": "Hello! Design a blue silk saree for a wedding",
                "language": "en",
            }
            await ws.send(json.dumps(message))
            print(f"3. Sent: {message['content']}")

            # 4. Receive response_start, chunks, and response_end
            received = []
            full_response = ""
            try:
                while True:
                    raw = await asyncio.wait_for(ws.recv(), timeout=60)
                    data = json.loads(raw)
                    received.append(data)
                    msg_type = data.get("type", "")

                    if msg_type == "response_start":
                        print(f"4. response_start (request_id: {data.get('request_id', '')[:8]}...)")
                    elif msg_type == "response_chunk":
                        pass  # Accumulate silently
                    elif msg_type == "response_end":
                        full_response = data.get("full_content", "")
                        print(f"5. response_end - {len(full_response)} chars")
                        break
            except asyncio.TimeoutError:
                print("   TIMEOUT waiting for response (60s)")
                return False

            # 5. Validate
            types_received = [r["type"] for r in received]
            has_start = "response_start" in types_received
            has_chunks = "response_chunk" in types_received
            has_end = "response_end" in types_received
            chunk_count = types_received.count("response_chunk")

            print(f"\n--- RESULTS ---")
            print(f"   response_start: {'YES' if has_start else 'NO'}")
            print(f"   response_chunk: {chunk_count} chunks")
            print(f"   response_end:   {'YES' if has_end else 'NO'}")
            print(f"   Response preview: {full_response[:200]}...")
            print(f"   Total messages:  {len(received)}")

            if has_start and has_chunks and has_end and len(full_response) > 10:
                print("\n>>> WEBSOCKET TEST PASSED <<<")
                return True
            else:
                print("\n>>> WEBSOCKET TEST FAILED <<<")
                return False

    except Exception as e:
        print(f"   WebSocket error: {e}")
        return False


if __name__ == "__main__":
    result = asyncio.run(test_websocket())
    sys.exit(0 if result else 1)
