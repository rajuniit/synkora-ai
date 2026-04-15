"""Tests for websocket.py."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest


class TestWebSocketMessage:
    """Tests for WebSocketMessage model."""

    def test_websocket_message_creation(self):
        """Test creating a WebSocketMessage."""
        from src.core.websocket import WebSocketMessage

        msg = WebSocketMessage(type="test", data={"key": "value"}, conversation_id="conv-123", message_id="msg-456")

        assert msg.type == "test"
        assert msg.data == {"key": "value"}
        assert msg.conversation_id == "conv-123"
        assert msg.message_id == "msg-456"

    def test_websocket_message_optional_fields(self):
        """Test WebSocketMessage with optional fields."""
        from src.core.websocket import WebSocketMessage

        msg = WebSocketMessage(type="test", data={})

        assert msg.conversation_id is None
        assert msg.message_id is None


class TestConnectionManagerInit:
    """Tests for ConnectionManager initialization."""

    def test_init(self):
        """Test ConnectionManager initialization."""
        from src.core.websocket import ConnectionManager

        manager = ConnectionManager()

        assert manager.active_connections == {}
        assert manager.rooms == {}
        assert manager.connection_metadata == {}


class TestConnect:
    """Tests for connect method."""

    @pytest.mark.asyncio
    async def test_connect_new_user(self):
        """Test connecting a new user."""
        from src.core.websocket import ConnectionManager

        manager = ConnectionManager()
        user_id = uuid4()
        tenant_id = uuid4()

        mock_websocket = AsyncMock()

        await manager.connect(mock_websocket, user_id, tenant_id)

        assert user_id in manager.active_connections
        assert mock_websocket in manager.active_connections[user_id]
        assert mock_websocket in manager.connection_metadata
        assert manager.connection_metadata[mock_websocket]["user_id"] == user_id
        mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_existing_user_multiple_connections(self):
        """Test connecting same user with multiple WebSockets."""
        from src.core.websocket import ConnectionManager

        manager = ConnectionManager()
        user_id = uuid4()
        tenant_id = uuid4()

        mock_websocket1 = AsyncMock()
        mock_websocket2 = AsyncMock()

        await manager.connect(mock_websocket1, user_id, tenant_id)
        await manager.connect(mock_websocket2, user_id, tenant_id)

        assert len(manager.active_connections[user_id]) == 2
        assert mock_websocket1 in manager.active_connections[user_id]
        assert mock_websocket2 in manager.active_connections[user_id]

    @pytest.mark.asyncio
    async def test_connect_sends_confirmation(self):
        """Test that connect sends confirmation message."""
        from src.core.websocket import ConnectionManager

        manager = ConnectionManager()
        user_id = uuid4()
        tenant_id = uuid4()

        mock_websocket = AsyncMock()

        await manager.connect(mock_websocket, user_id, tenant_id)

        # Should have sent connection confirmation
        mock_websocket.send_json.assert_called()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "connection"
        assert call_args["data"]["status"] == "connected"


class TestDisconnect:
    """Tests for disconnect method."""

    @pytest.mark.asyncio
    async def test_disconnect_removes_connection(self):
        """Test disconnecting removes the connection."""
        from src.core.websocket import ConnectionManager

        manager = ConnectionManager()
        user_id = uuid4()
        tenant_id = uuid4()

        mock_websocket = AsyncMock()
        await manager.connect(mock_websocket, user_id, tenant_id)

        manager.disconnect(mock_websocket)

        assert user_id not in manager.active_connections
        assert mock_websocket not in manager.connection_metadata

    @pytest.mark.asyncio
    async def test_disconnect_keeps_other_connections(self):
        """Test disconnecting one doesn't affect other connections."""
        from src.core.websocket import ConnectionManager

        manager = ConnectionManager()
        user_id = uuid4()
        tenant_id = uuid4()

        mock_websocket1 = AsyncMock()
        mock_websocket2 = AsyncMock()

        await manager.connect(mock_websocket1, user_id, tenant_id)
        await manager.connect(mock_websocket2, user_id, tenant_id)

        manager.disconnect(mock_websocket1)

        assert user_id in manager.active_connections
        assert mock_websocket2 in manager.active_connections[user_id]
        assert mock_websocket1 not in manager.active_connections[user_id]

    def test_disconnect_unknown_websocket(self):
        """Test disconnecting unknown WebSocket does nothing."""
        from src.core.websocket import ConnectionManager

        manager = ConnectionManager()
        mock_websocket = AsyncMock()

        # Should not raise
        manager.disconnect(mock_websocket)

    @pytest.mark.asyncio
    async def test_disconnect_removes_from_rooms(self):
        """Test disconnecting removes user from all rooms."""
        from src.core.websocket import ConnectionManager

        manager = ConnectionManager()
        user_id = uuid4()
        tenant_id = uuid4()

        mock_websocket = AsyncMock()
        await manager.connect(mock_websocket, user_id, tenant_id)

        # Join some rooms
        await manager.join_room("room1", user_id)
        await manager.join_room("room2", user_id)

        manager.disconnect(mock_websocket)

        # User should be removed from rooms
        assert user_id not in manager.rooms.get("room1", set())
        assert user_id not in manager.rooms.get("room2", set())


class TestSendPersonalMessage:
    """Tests for send_personal_message method."""

    @pytest.mark.asyncio
    async def test_send_personal_message_success(self):
        """Test sending personal message successfully."""
        from src.core.websocket import ConnectionManager

        manager = ConnectionManager()
        mock_websocket = AsyncMock()

        message = {"type": "test", "data": {"content": "Hello"}}
        await manager.send_personal_message(message, mock_websocket)

        mock_websocket.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_send_personal_message_handles_exception(self):
        """Test send_personal_message handles closed connection."""
        from src.core.websocket import ConnectionManager

        manager = ConnectionManager()
        user_id = uuid4()
        tenant_id = uuid4()

        mock_websocket = AsyncMock()
        mock_websocket.send_json = AsyncMock(side_effect=Exception("Connection closed"))

        # Connect first
        await manager.connect(mock_websocket, user_id, tenant_id)

        # Send should disconnect on error
        await manager.send_personal_message({"type": "test"}, mock_websocket)

        # Should have disconnected the websocket
        assert mock_websocket not in manager.connection_metadata


class TestSendToUser:
    """Tests for send_to_user method."""

    @pytest.mark.asyncio
    async def test_send_to_user_success(self):
        """Test sending to all user's connections."""
        from src.core.websocket import ConnectionManager

        manager = ConnectionManager()
        user_id = uuid4()
        tenant_id = uuid4()

        mock_websocket1 = AsyncMock()
        mock_websocket2 = AsyncMock()

        await manager.connect(mock_websocket1, user_id, tenant_id)
        await manager.connect(mock_websocket2, user_id, tenant_id)

        message = {"type": "test", "data": {}}
        await manager.send_to_user(message, user_id)

        mock_websocket1.send_json.assert_called_with(message)
        mock_websocket2.send_json.assert_called_with(message)

    @pytest.mark.asyncio
    async def test_send_to_user_not_connected(self):
        """Test sending to non-connected user does nothing."""
        from src.core.websocket import ConnectionManager

        manager = ConnectionManager()
        user_id = uuid4()

        # Should not raise
        await manager.send_to_user({"type": "test"}, user_id)

    @pytest.mark.asyncio
    async def test_send_to_user_cleans_up_failed(self):
        """Test that failed connections are cleaned up."""
        from src.core.websocket import ConnectionManager

        manager = ConnectionManager()
        user_id = uuid4()
        tenant_id = uuid4()

        mock_websocket = AsyncMock()
        mock_websocket.send_json = AsyncMock(side_effect=Exception("Connection closed"))

        await manager.connect(mock_websocket, user_id, tenant_id)
        await manager.send_to_user({"type": "test"}, user_id)

        # Failed connection should be cleaned up
        assert user_id not in manager.active_connections


class TestBroadcast:
    """Tests for broadcast method."""

    @pytest.mark.asyncio
    async def test_broadcast_to_all(self):
        """Test broadcasting to all connected users."""
        from src.core.websocket import ConnectionManager

        manager = ConnectionManager()

        user1 = uuid4()
        user2 = uuid4()
        tenant_id = uuid4()

        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()

        await manager.connect(mock_ws1, user1, tenant_id)
        await manager.connect(mock_ws2, user2, tenant_id)

        message = {"type": "broadcast", "data": {}}
        await manager.broadcast(message)

        mock_ws1.send_json.assert_called_with(message)
        mock_ws2.send_json.assert_called_with(message)

    @pytest.mark.asyncio
    async def test_broadcast_with_exclusion(self):
        """Test broadcasting with excluded users."""
        from src.core.websocket import ConnectionManager

        manager = ConnectionManager()

        user1 = uuid4()
        user2 = uuid4()
        tenant_id = uuid4()

        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()

        await manager.connect(mock_ws1, user1, tenant_id)
        await manager.connect(mock_ws2, user2, tenant_id)

        message = {"type": "broadcast", "data": {}}
        await manager.broadcast(message, exclude={user1})

        # User1 should NOT receive message
        # Check that send_json was called with broadcast message only for user2
        calls = [call for call in mock_ws2.send_json.call_args_list if call[0][0].get("type") == "broadcast"]
        assert len(calls) == 1


class TestRooms:
    """Tests for room management."""

    @pytest.mark.asyncio
    async def test_join_room_new(self):
        """Test joining a new room."""
        from src.core.websocket import ConnectionManager

        manager = ConnectionManager()
        user_id = uuid4()
        tenant_id = uuid4()

        # User must be connected first to join a room
        mock_ws = AsyncMock()
        await manager.connect(mock_ws, user_id, tenant_id)

        await manager.join_room("room1", user_id)

        assert "room1" in manager.rooms
        assert user_id in manager.rooms["room1"]

    @pytest.mark.asyncio
    async def test_join_room_existing(self):
        """Test joining an existing room."""
        from src.core.websocket import ConnectionManager

        manager = ConnectionManager()
        user1 = uuid4()
        user2 = uuid4()
        tenant_id = uuid4()

        # Users must be connected first
        await manager.connect(AsyncMock(), user1, tenant_id)
        await manager.connect(AsyncMock(), user2, tenant_id)

        await manager.join_room("room1", user1)
        await manager.join_room("room1", user2)

        assert len(manager.rooms["room1"]) == 2

    @pytest.mark.asyncio
    async def test_leave_room(self):
        """Test leaving a room."""
        from src.core.websocket import ConnectionManager

        manager = ConnectionManager()
        user_id = uuid4()
        tenant_id = uuid4()

        # User must be connected first
        await manager.connect(AsyncMock(), user_id, tenant_id)

        await manager.join_room("room1", user_id)
        manager.leave_room("room1", user_id)

        # Room should be deleted when empty
        assert "room1" not in manager.rooms

    @pytest.mark.asyncio
    async def test_leave_room_keeps_others(self):
        """Test leaving room keeps other users."""
        from src.core.websocket import ConnectionManager

        manager = ConnectionManager()
        user1 = uuid4()
        user2 = uuid4()
        tenant_id = uuid4()

        # Users must be connected first
        await manager.connect(AsyncMock(), user1, tenant_id)
        await manager.connect(AsyncMock(), user2, tenant_id)

        await manager.join_room("room1", user1)
        await manager.join_room("room1", user2)
        manager.leave_room("room1", user1)

        assert user2 in manager.rooms["room1"]
        assert user1 not in manager.rooms["room1"]

    def test_leave_nonexistent_room(self):
        """Test leaving a room that doesn't exist."""
        from src.core.websocket import ConnectionManager

        manager = ConnectionManager()
        user_id = uuid4()

        # Should not raise
        manager.leave_room("nonexistent", user_id)


class TestSendToRoom:
    """Tests for send_to_room method."""

    @pytest.mark.asyncio
    async def test_send_to_room_success(self):
        """Test sending to all users in a room."""
        from src.core.websocket import ConnectionManager

        manager = ConnectionManager()

        user1 = uuid4()
        user2 = uuid4()
        tenant_id = uuid4()

        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()

        await manager.connect(mock_ws1, user1, tenant_id)
        await manager.connect(mock_ws2, user2, tenant_id)

        await manager.join_room("room1", user1)
        await manager.join_room("room1", user2)

        message = {"type": "room_message", "data": {}}
        await manager.send_to_room("room1", message)

        # Check room message was sent to both users
        room_calls1 = [c for c in mock_ws1.send_json.call_args_list if c[0][0].get("type") == "room_message"]
        room_calls2 = [c for c in mock_ws2.send_json.call_args_list if c[0][0].get("type") == "room_message"]
        assert len(room_calls1) == 1
        assert len(room_calls2) == 1

    @pytest.mark.asyncio
    async def test_send_to_room_with_exclusion(self):
        """Test sending to room with excluded users."""
        from src.core.websocket import ConnectionManager

        manager = ConnectionManager()

        user1 = uuid4()
        user2 = uuid4()
        tenant_id = uuid4()

        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()

        await manager.connect(mock_ws1, user1, tenant_id)
        await manager.connect(mock_ws2, user2, tenant_id)

        await manager.join_room("room1", user1)
        await manager.join_room("room1", user2)

        message = {"type": "room_message", "data": {}}
        await manager.send_to_room("room1", message, exclude={user1})

        # Check room message was sent to user2
        room_calls = [c for c in mock_ws2.send_json.call_args_list if c[0][0].get("type") == "room_message"]
        assert len(room_calls) == 1

    @pytest.mark.asyncio
    async def test_send_to_nonexistent_room(self):
        """Test sending to nonexistent room does nothing."""
        from src.core.websocket import ConnectionManager

        manager = ConnectionManager()

        # Should not raise
        await manager.send_to_room("nonexistent", {"type": "test"})


class TestStreamMessage:
    """Tests for stream_message method."""

    @pytest.mark.asyncio
    async def test_stream_message(self):
        """Test streaming a message chunk."""
        from src.core.websocket import ConnectionManager

        manager = ConnectionManager()
        user_id = uuid4()
        tenant_id = uuid4()

        mock_websocket = AsyncMock()
        await manager.connect(mock_websocket, user_id, tenant_id)

        await manager.stream_message(
            conversation_id="conv-123", message_id="msg-456", content_chunk="Hello", user_id=user_id, is_final=False
        )

        # Check the message format
        calls = mock_websocket.send_json.call_args_list
        stream_calls = [c for c in calls if c[0][0].get("type") == "message_stream"]
        assert len(stream_calls) == 1

        msg = stream_calls[0][0][0]
        assert msg["data"]["conversation_id"] == "conv-123"
        assert msg["data"]["content"] == "Hello"
        assert msg["data"]["is_final"] is False


class TestSendTypingIndicator:
    """Tests for send_typing_indicator method."""

    @pytest.mark.asyncio
    async def test_send_typing_indicator(self):
        """Test sending typing indicator."""
        from src.core.websocket import ConnectionManager

        manager = ConnectionManager()
        user1 = uuid4()
        user2 = uuid4()
        tenant_id = uuid4()

        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()

        await manager.connect(mock_ws1, user1, tenant_id)
        await manager.connect(mock_ws2, user2, tenant_id)

        # Both join conversation room
        await manager.join_room("conversation:conv-123", user1)
        await manager.join_room("conversation:conv-123", user2)

        # User1 sends typing indicator
        await manager.send_typing_indicator("conv-123", user1, is_typing=True)

        # User2 should receive it, but not user1
        typing_calls = [c for c in mock_ws2.send_json.call_args_list if c[0][0].get("type") == "typing"]
        assert len(typing_calls) == 1


class TestSendError:
    """Tests for send_error method."""

    @pytest.mark.asyncio
    async def test_send_error(self):
        """Test sending error message."""
        from src.core.websocket import ConnectionManager

        manager = ConnectionManager()
        mock_websocket = AsyncMock()

        await manager.send_error("Something went wrong", mock_websocket, "ERR_001")

        mock_websocket.send_json.assert_called_once()
        msg = mock_websocket.send_json.call_args[0][0]
        assert msg["type"] == "error"
        assert msg["data"]["error"] == "Something went wrong"
        assert msg["data"]["code"] == "ERR_001"


class TestStatsMethods:
    """Tests for stats methods."""

    @pytest.mark.asyncio
    async def test_get_user_count(self):
        """Test getting connected user count."""
        from src.core.websocket import ConnectionManager

        manager = ConnectionManager()

        assert manager.get_user_count() == 0

        user1 = uuid4()
        user2 = uuid4()
        tenant_id = uuid4()

        await manager.connect(AsyncMock(), user1, tenant_id)
        await manager.connect(AsyncMock(), user2, tenant_id)

        assert manager.get_user_count() == 2

    @pytest.mark.asyncio
    async def test_get_connection_count(self):
        """Test getting total connection count."""
        from src.core.websocket import ConnectionManager

        manager = ConnectionManager()

        assert manager.get_connection_count() == 0

        user_id = uuid4()
        tenant_id = uuid4()

        await manager.connect(AsyncMock(), user_id, tenant_id)
        await manager.connect(AsyncMock(), user_id, tenant_id)

        assert manager.get_connection_count() == 2

    @pytest.mark.asyncio
    async def test_is_user_connected(self):
        """Test checking if user is connected."""
        from src.core.websocket import ConnectionManager

        manager = ConnectionManager()
        user_id = uuid4()
        tenant_id = uuid4()

        assert manager.is_user_connected(user_id) is False

        await manager.connect(AsyncMock(), user_id, tenant_id)

        assert manager.is_user_connected(user_id) is True


class TestRoomAuthorization:
    """Tests for room authorization feature."""

    @pytest.mark.asyncio
    async def test_join_room_with_authorization_callback(self):
        """Test joining a room with authorization callback."""
        from src.core.websocket import ConnectionManager

        # Create authorization callback that allows access
        async def allow_all(room_id, user_id, tenant_id):
            return True

        manager = ConnectionManager(room_authorization_callback=allow_all)
        user_id = uuid4()
        tenant_id = uuid4()

        await manager.connect(AsyncMock(), user_id, tenant_id)
        await manager.join_room("room1", user_id)

        assert user_id in manager.rooms["room1"]

    @pytest.mark.asyncio
    async def test_join_room_denied_by_authorization(self):
        """Test joining a room denied by authorization."""
        from src.core.websocket import ConnectionManager, RoomAuthorizationError

        # Create authorization callback that denies access
        async def deny_all(room_id, user_id, tenant_id):
            return False

        manager = ConnectionManager(room_authorization_callback=deny_all)
        user_id = uuid4()
        tenant_id = uuid4()

        await manager.connect(AsyncMock(), user_id, tenant_id)

        with pytest.raises(RoomAuthorizationError):
            await manager.join_room("room1", user_id)

        assert "room1" not in manager.rooms

    @pytest.mark.asyncio
    async def test_join_room_skip_authorization(self):
        """Test joining a room with skip_authorization flag."""
        from src.core.websocket import ConnectionManager

        # Create authorization callback that denies access
        async def deny_all(room_id, user_id, tenant_id):
            return False

        manager = ConnectionManager(room_authorization_callback=deny_all)
        user_id = uuid4()
        tenant_id = uuid4()

        await manager.connect(AsyncMock(), user_id, tenant_id)

        # Should succeed because we skip authorization
        await manager.join_room("room1", user_id, skip_authorization=True)

        assert user_id in manager.rooms["room1"]

    @pytest.mark.asyncio
    async def test_join_room_requires_connection(self):
        """Test joining a room requires user to be connected."""
        from src.core.websocket import ConnectionManager, RoomAuthorizationError

        async def allow_all(room_id, user_id, tenant_id):
            return True

        manager = ConnectionManager(room_authorization_callback=allow_all)
        user_id = uuid4()

        # User is not connected
        with pytest.raises(RoomAuthorizationError) as exc_info:
            await manager.join_room("room1", user_id)

        assert "must be connected" in str(exc_info.value.message)

    @pytest.mark.asyncio
    async def test_set_room_authorization_callback(self):
        """Test setting room authorization callback after init."""
        from src.core.websocket import ConnectionManager, RoomAuthorizationError

        manager = ConnectionManager()
        user_id = uuid4()
        tenant_id = uuid4()

        await manager.connect(AsyncMock(), user_id, tenant_id)

        # Initially no callback - should allow
        await manager.join_room("room1", user_id)
        assert user_id in manager.rooms["room1"]

        # Set callback that denies
        async def deny_all(room_id, user_id, tenant_id):
            return False

        manager.set_room_authorization_callback(deny_all)

        # Now should be denied
        with pytest.raises(RoomAuthorizationError):
            await manager.join_room("room2", user_id)

    @pytest.mark.asyncio
    async def test_send_to_room_with_sender_verification(self):
        """Test send_to_room verifies sender is in room."""
        from src.core.websocket import ConnectionManager

        manager = ConnectionManager()
        user1 = uuid4()
        user2 = uuid4()
        tenant_id = uuid4()

        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()

        await manager.connect(mock_ws1, user1, tenant_id)
        await manager.connect(mock_ws2, user2, tenant_id)

        # Only user2 joins the room
        await manager.join_room("room1", user2)

        message = {"type": "test", "data": {}}

        # User1 tries to send to room but is not a member
        await manager.send_to_room("room1", message, sender_user_id=user1)

        # User2 should NOT receive the message because user1 is not authorized
        msg_calls = [c for c in mock_ws2.send_json.call_args_list if c[0][0].get("type") == "test"]
        assert len(msg_calls) == 0

    @pytest.mark.asyncio
    async def test_is_user_in_room(self):
        """Test is_user_in_room method."""
        from src.core.websocket import ConnectionManager

        manager = ConnectionManager()
        user_id = uuid4()
        tenant_id = uuid4()

        await manager.connect(AsyncMock(), user_id, tenant_id)

        assert manager.is_user_in_room("room1", user_id) is False

        await manager.join_room("room1", user_id)

        assert manager.is_user_in_room("room1", user_id) is True

    @pytest.mark.asyncio
    async def test_get_user_tenant_id(self):
        """Test getting tenant_id for a connected user."""
        from src.core.websocket import ConnectionManager

        manager = ConnectionManager()
        user_id = uuid4()
        tenant_id = uuid4()

        # Not connected
        assert manager.get_user_tenant_id(user_id) is None

        await manager.connect(AsyncMock(), user_id, tenant_id)

        assert manager.get_user_tenant_id(user_id) == tenant_id
