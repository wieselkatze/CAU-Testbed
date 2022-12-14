package de.cau.testbed.server;

import de.cau.testbed.server.config.HardwareNode;
import de.cau.testbed.server.config.TestbedServerConfiguration;
import de.cau.testbed.server.config.datastore.User;
import de.cau.testbed.server.config.datastore.yaml.YAMLDatabase;
import de.cau.testbed.server.constants.KafkaConstants;
import de.cau.testbed.server.module.*;
import de.cau.testbed.server.network.KafkaNetworkReceiver;
import de.cau.testbed.server.network.KafkaNetworkSender;
import de.cau.testbed.server.resources.AdminResource;
import de.cau.testbed.server.resources.ExperimentResource;
import de.cau.testbed.server.resources.UploadFirmwareResource;
import de.cau.testbed.server.security.ApiKeyAuthenticator;
import de.cau.testbed.server.security.ApiKeyAuthorizer;
import de.cau.testbed.server.service.ExperimentService;
import de.cau.testbed.server.service.FirmwareService;
import de.cau.testbed.server.service.NodeService;
import de.cau.testbed.server.service.UserService;
import de.cau.testbed.server.util.ExperimentFinishTrackerFactory;
import de.cau.testbed.server.util.PathUtil;
import de.cau.testbed.server.util.event.LogRetrievedEvent;
import io.dropwizard.auth.AuthDynamicFeature;
import io.dropwizard.auth.AuthValueFactoryProvider;
import io.dropwizard.auth.basic.BasicCredentialAuthFilter;
import io.dropwizard.core.Application;
import io.dropwizard.core.setup.Bootstrap;
import io.dropwizard.core.setup.Environment;
import io.dropwizard.forms.MultiPartBundle;
import org.glassfish.jersey.server.filter.RolesAllowedDynamicFeature;

import java.util.List;
import java.util.concurrent.SubmissionPublisher;
import java.util.stream.Collectors;

public class TestbedServerApplication extends Application<TestbedServerConfiguration> {
    public static void main(String[] args) throws Exception {
        new TestbedServerApplication().run(args);
    }

    @Override
    public void initialize(Bootstrap<TestbedServerConfiguration> bootstrap) {
        super.initialize(bootstrap);
        bootstrap.addBundle(new MultiPartBundle());
    }

    @Override
    public void run(TestbedServerConfiguration configuration, Environment environment) {
        PathUtil.initialize(configuration.workingDirectory);
        KafkaNetworkSender.setKafkaAddress(configuration.kafkaAddress);
        KafkaNetworkReceiver.setKafkaAddress(configuration.kafkaAddress);

        final YAMLDatabase database = new YAMLDatabase(configuration.workingDirectory);
        registerAuthorizationComponent(environment, database);

        final List<NodeStatusObject> nodeStatusList = createHeartbeatThread(configuration.nodes, configuration.heartbeatInterval);
        createFirmwareDistributionThreads(configuration.numFirmwareDistributionThreads);

        // Setup for event-based pipeline between log retrieval threads and trackers
        final SubmissionPublisher<LogRetrievedEvent> logRetrievedHandler = new SubmissionPublisher<>();
        final ExperimentFinishTrackerFactory trackerFactory = new ExperimentFinishTrackerFactory(logRetrievedHandler);
        createLogRetrievalThreads(configuration.numLogRetrievalThreads, logRetrievedHandler);

        // Create trackers for experiments that have started before execution of server
        trackerFactory.createInitialTrackers(database);

        // Create scheduling thread that handles initiation of experiments
        final ExperimentSchedulingThread schedulingThread = new ExperimentSchedulingThread(database, trackerFactory);
        schedulingThread.start();

        // Services handle backend stuff for the front-end REST API
        final ExperimentService experimentService = new ExperimentService(database, configuration.nodes, schedulingThread);
        final FirmwareService firmwareService = new FirmwareService(database);
        final UserService userService = new UserService(database.getUserDatabase());
        final NodeService nodeService = new NodeService(nodeStatusList);

        // XYZResources provide the REST API for interaction and utilize the according services in the background
        environment.jersey().register(new ExperimentResource(experimentService));
        environment.jersey().register(new UploadFirmwareResource(firmwareService));
        environment.jersey().register(new AdminResource(userService, nodeService));
    }

    private void createLogRetrievalThreads(int numLogRetrievalThreads, SubmissionPublisher<LogRetrievedEvent> trackerFactory) {
        for (int i = 0; i < numLogRetrievalThreads; i++)
            new LogRetrievalThread(trackerFactory, i).start();
    }

    private void createFirmwareDistributionThreads(int numFirmwareDistributionThreads) {
        for (int i = 0; i < numFirmwareDistributionThreads; i++)
            new FirmwareDistributionThread(i).start();
    }

    private void registerAuthorizationComponent(Environment environment, YAMLDatabase database) {
        environment.jersey().register(new AuthDynamicFeature(new BasicCredentialAuthFilter.Builder<User>()
                .setAuthenticator(new ApiKeyAuthenticator(database.getUserDatabase()))
                .setAuthorizer(new ApiKeyAuthorizer())
                .setRealm("API-KEY-AUTH-REALM")
                .buildAuthFilter()
        ));

        environment.jersey().register(new RolesAllowedDynamicFeature());
        environment.jersey().register(new AuthValueFactoryProvider.Binder<>(User.class));
    }

    private List<NodeStatusObject> createHeartbeatThread(List<HardwareNode> hardwareNodeList, int heartbeatInterval) {
        final HeartbeatThread thread = new HeartbeatThread(
                hardwareNodeList.stream().map(x -> x.id).collect(Collectors.toList()),
                heartbeatInterval
        );

        thread.start();

        return thread.getNodeStatusList();
    }
}