package de.cau.testbed.server.config.datastore;

import de.cau.testbed.server.constants.UserType;

import java.util.Optional;

/**
 * Wrapper/interface for the user database.
 */
public interface UserDatabase {
    Optional<User> getUserById(long id);

    Optional<User> getUserByApiKey(String apiKey);

    User addUser(String name, UserType type);
}
