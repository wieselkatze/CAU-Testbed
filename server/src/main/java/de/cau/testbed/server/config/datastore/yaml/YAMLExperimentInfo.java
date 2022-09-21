package de.cau.testbed.server.config.datastore.yaml;

import com.fasterxml.jackson.annotation.JsonProperty;
import de.cau.testbed.server.constants.ExperimentStatus;

import java.time.LocalDateTime;

/**
 * Data representation for an individual entry in the 'experiments.yaml' file that contains information about
 * start, stop, name, owner and experiment ID, which is used for linking to the individual
 * configuration file.
 */
public class YAMLExperimentInfo {
    public final long owner;
    public final long experimentId;
    public final String name;
    public final ExperimentStatus status;
    public final LocalDateTime start;

    public final LocalDateTime end;

    public YAMLExperimentInfo(
            @JsonProperty("name") String name,
            @JsonProperty("owner") long ownerId,
            @JsonProperty("experimentId") long experimentId,
            @JsonProperty("status") ExperimentStatus status,
            @JsonProperty("start") LocalDateTime start,
            @JsonProperty("end")LocalDateTime end
            ) {
        this.name = name;
        this.owner = ownerId;
        this.experimentId = experimentId;
        this.status = status;
        this.start = start;
        this.end = end;
    }

    @Override
    public String toString() {
        return "YAMLExperimentStatus{" +
                "owner='" + owner + '\'' +
                ", experimentId='" + experimentId + '\'' +
                ", name='" + name + '\'' +
                ", status=" + status +
                '}';
    }
}
