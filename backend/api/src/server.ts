import app from './app';
import { config } from './shared/config';
import { connectDatabase } from './shared/config/database';
import { setupWorker } from './modules/jobs/processor.worker';

const startServer = async () => {
    // Connect to Database
    await connectDatabase();

    // Start background worker
    setupWorker();

    // Start Express Server
    app.listen(config.port, () => {
        console.log(`Server running in ${config.nodeEnv} mode on port ${config.port}`);
    });
};

startServer();
