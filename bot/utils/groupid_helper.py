class GroupIdHelper:

    @staticmethod
    def normalize_group_id(group_id):

        if isinstance(group_id, str):
            # If it's already a string, check if it's a negative supergroup ID
            if group_id.startswith('-'):
                try:
                    numeric_id = int(group_id)
                    if numeric_id < -1000000000000:
                        # This is a supergroup ID, convert to stored format
                        return str(abs(numeric_id + 1000000000000))
                    else:
                        # Regular negative group ID
                        return str(abs(numeric_id))
                except ValueError:
                    return group_id
            else:
                # Positive string ID
                return group_id
        elif isinstance(group_id, int):
            if group_id < -1000000000000:
                # Supergroup ID format
                return str(abs(group_id + 1000000000000))
            elif group_id < 0:
                # Regular negative group ID
                return str(abs(group_id))
            else:
                # Positive group ID
                return str(group_id)
        else:
            return str(group_id)
    
    @staticmethod
    def to_telegram_format(stored_group_id):
        try:
            if isinstance(stored_group_id, str):
                if stored_group_id.startswith('-'):
                    # Already in correct format
                    return int(stored_group_id)
                else:
                    # Convert stored format to supergroup format
                    numeric_id = int(stored_group_id)
                    return -1000000000000 - numeric_id
            elif isinstance(stored_group_id, int):
                if stored_group_id < 0:
                    # Already in correct format
                    return stored_group_id
                else:
                    # Convert to supergroup format
                    return -1000000000000 - stored_group_id
            else:
                # Fallback
                return int(stored_group_id)
        except (ValueError, TypeError):
            print(f"Warning: Could not convert group ID {stored_group_id}")
            return stored_group_id
    
    @staticmethod
    def get_search_group_id(group_id):
        return GroupIdHelper.normalize_group_id(group_id)
    
    @staticmethod
    def log_group_conversion(original_id, converted_id, operation="conversion"):
        print(f"🔄 Group ID {operation}: {original_id} -> {converted_id}")