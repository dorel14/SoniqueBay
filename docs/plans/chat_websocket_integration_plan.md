# Plan: Chat WebSocket Integration

## Information Gathered

After analyzing the codebase, I've identified the following components:

1. **Chat Component** (`frontend/pages/components/layout/chat.py`):
   - Currently displays messages from `state.chat_messages`
   - Uses `@ui.refreshable` to update when needed
   - No WebSocket connection for real-time updates

2. **Right Drawer** (`frontend/pages/components/layout/right_drawer.py`):
   - Contains the chat component in a tab panel
   - Has a message input field but no send functionality
   - Needs alignment improvements for the chat section

3. **WebSocket Services**:
   - `frontend/services/central_websocket_service.py` provides WebSocket functionality
   - Supports multiple channels including 'chat'
   - Has methods for connecting, registering handlers, and sending messages

4. **Backend WebSocket Endpoint**:
   - `/chat/ws` endpoint in `backend/api/routers/chat_api.py`
   - Accepts JSON messages and streams responses

## Plan

### 1. Create a Chat Service

Create a new file `frontend/services/chat_service.py` to handle chat-specific WebSocket operations:
- Connect to the WebSocket on the 'chat' channel
- Register handlers for incoming messages
- Provide methods to send messages
- Format messages for display

### 2. Update Chat Component

Modify `frontend/pages/components/layout/chat.py` to:
- Add a method to send messages
- Register a handler for incoming messages
- Update the UI when new messages arrive
- Improve scrolling behavior

### 3. Update Right Drawer

Modify `frontend/pages/components/layout/right_drawer.py` to:
- Connect the input field to the send_message function
- Add a send button
- Improve the chat UI alignment with proper Tailwind classes
- Ensure the chat container takes appropriate space

### 4. Connect Everything Together

- Initialize the chat service when the app starts
- Ensure the WebSocket connection is established
- Make sure messages are properly stored in the app state

## Dependent Files to be Edited

1. `frontend/pages/components/layout/chat.py` - Main chat component
2. `frontend/pages/components/layout/right_drawer.py` - Container for chat
3. `frontend/services/chat_service.py` - New file for chat WebSocket handling
4. `frontend/utils/app_state.py` - May need updates for chat message handling

## Followup Steps

1. **Testing**:
   - Test sending and receiving messages
   - Verify that the UI updates correctly
   - Test with multiple users/browsers

2. **Styling Verification**:
   - Check alignment in different screen sizes
   - Ensure the chat is properly scrollable
   - Verify that the input field and send button are properly aligned

3. **Error Handling**:
   - Add proper error handling for WebSocket disconnections
   - Implement reconnection logic
   - Show appropriate error messages to users
