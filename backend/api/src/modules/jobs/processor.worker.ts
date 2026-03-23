import { Worker, Job } from 'bullmq';
import { config } from '../../shared/config';
import Project, { ProjectStatus } from '../projects/project.model';
import { FcmService } from '../../shared/services/fcm.service';
import { spawn } from 'child_process';
import path from 'path';

const connection = {
    url: config.redis.url,
    maxRetriesPerRequest: null,
};

export const setupWorker = () => {
    const worker = new Worker('reconstruction-processing', async (job: Job) => {
        const { projectId } = job.data;
        console.log(` Starting real processing for project: ${projectId}`);

        try {
            const project = await Project.findById(projectId);
            if (!project) {
                console.error(`Project ${projectId} not found`);
                return;
            }

            // Path to the Python processor
            const processorPath = path.join(__dirname, '../../../../processor');
            const pythonExecutable = path.join(processorPath, 'venv/bin/python3');
            
            return new Promise((resolve, reject) => {
                const pythonProcess = spawn(pythonExecutable, [
                    'main.py', 
                    '--job_id', projectId,
                    '--run_pipeline' 
                ], {
                    cwd: processorPath
                });

                pythonProcess.stdout.on('data', (data) => {
                    console.log(`[Python]: ${data}`);
                });

                pythonProcess.stderr.on('data', (data) => {
                    console.error(`[Python Error]: ${data}`);
                });

                pythonProcess.on('close', async (code) => {
                    if (code === 0) {
                        console.log(` Pipeline finished for project: ${projectId}`);
                        
                        const downloadUrl = `http://${config.network.localIp}:${config.port}/models/${projectId}/model.ply`;
                        
                        project.status = ProjectStatus.COMPLETED;
                        project.modelUrl = downloadUrl;
                        await project.save();

                        if (project.fcmToken) {
                            await FcmService.sendNotification(
                                project.fcmToken,
                                '3D Model Ready!',
                                `Your reconstruction for "${project.name}" is complete.`,
                                { projectId, downloadUrl, type: 'RECONSTRUCTION_COMPLETE' }
                            );
                        }
                        resolve(true);
                    } else {
                        console.error(` Pipeline failed with code ${code}`);
                        project.status = ProjectStatus.FAILED;
                        await project.save();
                        reject(new Error(`Pipeline failed with code ${code}`));
                    }
                });
            });
        } catch (error) {
            console.error(`Error processing job ${job.id}:`, error);
            throw error;
        }
    }, { connection });

    worker.on('completed', (job) => {
        console.log(`Job ${job.id} has completed!`);
    });

    worker.on('failed', (job, err) => {
        console.error(`Job ${job?.id} has failed with ${err.message}`);
    });

    return worker;
};
