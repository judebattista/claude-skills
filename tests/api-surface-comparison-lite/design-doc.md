# UserService API Design

## Overview

The UserService provides basic CRUD operations on User objects.

## API

### `get_user(user_id: int) -> User`

Returns the User object for the given ID. Raises `NotFoundError` if the user does not exist.

### `create_user(name: str, email: str) -> User`

Creates a new User with the given name and email. Returns the created User object.

### `delete_user(user_id: int) -> None`

Permanently deletes the user with the given ID. Raises `NotFoundError` if the user does not exist.

### `list_users() -> list[User]`

Returns all users in the system as a list.
