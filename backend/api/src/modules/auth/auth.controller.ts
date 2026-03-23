import { Request, Response } from 'express';
import jwt from 'jsonwebtoken';
import { twilioService } from './twilio.service';
import { config } from '../../shared/config';

export class AuthController {
    /**
     * Request an OTP for a phone number
     */
    static async requestOtp(req: Request, res: Response) {
        const { phoneNumber } = req.body;
        console.log(`Received OTP request for phone: ${phoneNumber}`);

        if (!phoneNumber) {
            console.log('OTP Request failed: Phone number missing');
            return res.status(400).json({ message: 'Phone number is required' });
        }

        try {
            // Development Bypass for User
            if (phoneNumber === '+918595192809') {
                console.log('🚨 DEVELOPMENT BYPASS: Using fixed OTP 123456 for +918595192809');
                return res.status(200).json({ message: 'OTP sent (Bypass Active: 123456)' });
            }

            await twilioService.sendVerificationCode(phoneNumber);
            console.log(`OTP sent successfully to: ${phoneNumber}`);
            return res.status(200).json({ message: 'OTP sent successfully' });
        } catch (error: any) {
            console.error(`OTP Request error for ${phoneNumber}:`, error.message);
            return res.status(500).json({ message: error.message });
        }
    }

    /**
     * Verify an OTP and return a JWT
     */
    static async verifyOtp(req: Request, res: Response) {
        const { phoneNumber, code } = req.body;

        if (!phoneNumber || !code) {
            return res.status(400).json({ message: 'Phone number and code are required' });
        }

        try {
            let isValid = false;

            // Development Bypass for User
            if (phoneNumber === '+918595192809' && code === '123456') {
                console.log('🚨 DEVELOPMENT BYPASS: Verifying with fixed OTP');
                isValid = true;
            } else {
                isValid = await twilioService.checkVerificationCode(phoneNumber, code);
            }

            if (!isValid) {
                return res.status(401).json({ message: 'Invalid or expired OTP' });
            }

            // Generate JWT
            const token = jwt.sign(
                { phoneNumber },
                config.jwt.secret,
                { expiresIn: config.jwt.expiresIn as any }
            );

            return res.status(200).json({
                message: 'Authentication successful',
                token,
                user: { phoneNumber }
            });
        } catch (error: any) {
            return res.status(500).json({ message: error.message });
        }
    }
}
