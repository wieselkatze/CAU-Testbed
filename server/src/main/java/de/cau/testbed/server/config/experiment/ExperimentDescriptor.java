package de.cau.testbed.server.config.experiment;

import de.cau.testbed.server.config.datastore.User;
import de.cau.testbed.server.constants.ExperimentStatus;

import java.time.LocalDateTime;
import java.util.List;

/**
 * Describes an experiment with all its nodes/components.
 * This is a wrapper that provides abstraction from the database in the background.
 * Provides all necessary information about an experiment and means to manipulate the status of it.
 */
public interface ExperimentDescriptor {
    long getId();

    String getName();

    User getOwner();

    LocalDateTime getStart();

    LocalDateTime getEnd();

    ExperimentStatus getStatus();

    void setStatus(ExperimentStatus status);

    List<ExperimentNode> getNodes();

    Object getLockObject();
}
