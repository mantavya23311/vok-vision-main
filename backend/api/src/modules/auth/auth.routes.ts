import { Router } from 'express';
import { AuthController } from './auth.controller';

const router = Router();

// @route   POST /api/v1/auth/otp/request
// @desc    Request a verification code via SMS
router.post('/otp/request', AuthController.requestOtp);

// @route   POST /api/v1/auth/otp/verify
// @desc    Verify the code and return a JWT Access Token
router.post('/otp/verify', AuthController.verifyOtp);

export default router;
