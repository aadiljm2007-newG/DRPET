import asyncio
import websockets
import json
import traceback

async def test_backend():
    uri = "wss://aadiljm-drpet.hf.space/ws/stream?node_id=backend_diagnostic_test"
    print(f"Connecting to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected successfully!")
            
            with open("bus.jpg", "rb") as f:
                dummy_jpeg = f.read()
            
            print("Sending test frame...")
            await websocket.send(dummy_jpeg)
            
            print("Waiting for response...")
            response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
            
            data = json.loads(response)
            status = data.get("status")
            print(f"Received valid architecture response! Status: {status}")
            
    except Exception as e:
        print(f"Diagnostic Failure:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_backend())
