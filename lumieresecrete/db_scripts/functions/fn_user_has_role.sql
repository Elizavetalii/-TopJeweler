CREATE OR REPLACE FUNCTION fn_user_has_role(user_id INT, role_name VARCHAR)
RETURNS BOOLEAN AS $$
DECLARE
    role_count INT;
BEGIN
    SELECT COUNT(*)
    INTO role_count
    FROM UserRole ur
    JOIN Roles r ON ur.RoleID = r.RoleID
    WHERE ur.UserID = user_id AND r.RoleName = role_name;

    RETURN role_count > 0;
END;
$$ LANGUAGE plpgsql;