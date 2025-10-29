import toast from 'react-hot-toast';
import { ToastInput } from '../types';

export function showToast({ type, message }: ToastInput) {
    switch (type) {
        case 'success':
            toast.success(message);
            break;
        case 'error':
            toast.error(message);
            break;
        default:
            toast(message);
    }
}