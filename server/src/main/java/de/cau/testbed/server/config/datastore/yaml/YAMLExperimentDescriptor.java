package de.cau.testbed.server.config.datastore.yaml;

import de.cau.testbed.server.config.datastore.User;
import de.cau.testbed.server.config.datastore.UserDatabase;
import de.cau.testbed.server.config.experiment.*;
import de.cau.testbed.server.constants.ExperimentStatus;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

/**
 * Wrapper for the {@link ExperimentDescriptor} interface for the YAML data store.
 * Ties together the 'experiments.yaml' ({@link YAMLExperimentList}) and the individual
 * 'configuration.yaml' ({@link YAMLExperimentInfo}) files into one accessible class.
 */
public class YAMLExperimentDescriptor implements ExperimentDescriptor {
    private final long id;

    private final User owner;
    private final String name;
    private final LocalDateTime start;
    private final LocalDateTime end;
    private final YAMLDatabase database;
    private ExperimentStatus status;
    private final List<ExperimentNode> nodes;

    // Used for synchronization of reading and writing the experiment status
    private final Object lockObject = new Object();

    public YAMLExperimentDescriptor(YAMLDatabase database, YAMLExperimentInfo experimentInfo, YAMLExperimentDetail experimentDetail, UserDatabase userTable) {
        this.database = database;
        final Optional<User> user = userTable.getUserById(experimentInfo.owner());

        this.owner = user.orElseThrow(() -> new IllegalArgumentException(String.format(
                "Could not instantiate experiment %d; user not found!",
                experimentInfo.experimentId()
        )));

        this.id = experimentInfo.experimentId();
        this.name = experimentInfo.name();
        this.start = experimentInfo.start();
        this.end = experimentInfo.end();
        this.nodes = experimentDetail.nodes();
        this.status = experimentInfo.status();
    }

    @Override
    public long getId() {
        return id;
    }

    @Override
    public String getName() {
        return name;
    }

    @Override
    public User getOwner() {
        return owner;
    }

    @Override
    public LocalDateTime getStart() {
        return start;
    }

    @Override
    public LocalDateTime getEnd() {
        return end;
    }

    @Override
    public ExperimentStatus getStatus() {
        return status;
    }

    @Override
    public void setStatus(ExperimentStatus status) {
        this.status = status;
        database.updateExperiment(this);
    }

    @Override
    public List<ExperimentNode> getNodes() {
        return nodes;
    }

    @Override
    public Object getLockObject() {
        return lockObject;
    }

    @Override
    public String toString() {
        return "YAMLExperimentDescriptor{" +
                "id='" + id + '\'' +
                ", owner='" + owner + '\'' +
                ", name='" + name + '\'' +
                ", start=" + start +
                ", end=" + end +
                ", nodes=" + nodes +
                '}';
    }
}
