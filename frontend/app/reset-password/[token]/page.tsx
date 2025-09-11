'use client';

import { useState, use } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Lock, CheckCircle, AlertCircle, Loader2, Eye, EyeOff } from 'lucide-react';
import { api } from '@/lib/api-client';
import { useMutation } from '@tanstack/react-query';
import { notifications } from '@/lib/notification-service';

interface PageProps {
  params: Promise<{
    token: string;
  }>;
}

export default function ResetPasswordPage({ params }: PageProps) {
  const { token } = use(params);
  const router = useRouter();
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  const resetPassword = useMutation({
    mutationFn: async (newPassword: string) => {
      return api.auth.resetPassword({ token: token, new_password: newPassword });
    },
    onSuccess: () => {
      setIsSuccess(true);
      notifications.success('Password reset successful', 'You can now log in with your new password.');
      
      // Redirect to login after 3 seconds
      setTimeout(() => {
        router.push('/login');
      }, 3000);
    },
    onError: (error) => {
      notifications.handleApiError(error, 'Failed to reset password');
    },
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validate passwords
    if (password.length < 8) {
      notifications.error('Password too short', 'Password must be at least 8 characters long.');
      return;
    }
    
    if (password !== confirmPassword) {
      notifications.error('Passwords do not match', 'Please make sure both passwords are the same.');
      return;
    }
    
    resetPassword.mutate(password);
  };

  const getPasswordStrength = (password: string) => {
    if (password.length === 0) return { strength: 'none', color: 'bg-gray-200' };
    if (password.length < 6) return { strength: 'weak', color: 'bg-red-500' };
    if (password.length < 8) return { strength: 'fair', color: 'bg-yellow-500' };
    if (password.match(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])/)) {
      return { strength: 'strong', color: 'bg-green-500' };
    }
    return { strength: 'good', color: 'bg-blue-500' };
  };

  const passwordStrength = getPasswordStrength(password);

  if (isSuccess) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Card className="w-[400px]">
          <CardHeader className="text-center">
            <div className="mx-auto w-12 h-12 rounded-full bg-green-500/10 flex items-center justify-center mb-4">
              <CheckCircle className="h-6 w-6 text-green-500" />
            </div>
            <CardTitle>Password reset successful!</CardTitle>
            <CardDescription>
              Your password has been reset. Redirecting to login...
            </CardDescription>
          </CardHeader>
          <CardFooter>
            <Link href="/login" className="w-full">
              <Button className="w-full gradient-primary">
                Go to Login
              </Button>
            </Link>
          </CardFooter>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <Card className="w-[400px]">
        <CardHeader className="text-center">
          <CardTitle>Reset your password</CardTitle>
          <CardDescription>
            Enter your new password below
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="password">New Password</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Enter new password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  disabled={resetPassword.isPending}
                  className="pr-10"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-0 top-0 h-full px-3 hover:bg-transparent"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </Button>
              </div>
              {password && (
                <div className="space-y-1">
                  <div className="flex gap-1">
                    <div className={`h-1 flex-1 rounded-full ${password.length > 0 ? passwordStrength.color : 'bg-gray-200'}`} />
                    <div className={`h-1 flex-1 rounded-full ${password.length >= 6 ? passwordStrength.color : 'bg-gray-200'}`} />
                    <div className={`h-1 flex-1 rounded-full ${password.length >= 8 ? passwordStrength.color : 'bg-gray-200'}`} />
                    <div className={`h-1 flex-1 rounded-full ${passwordStrength.strength === 'strong' ? passwordStrength.color : 'bg-gray-200'}`} />
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Password strength: {passwordStrength.strength}
                  </p>
                </div>
              )}
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="confirmPassword">Confirm Password</Label>
              <div className="relative">
                <Input
                  id="confirmPassword"
                  type={showConfirmPassword ? 'text' : 'password'}
                  placeholder="Confirm new password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  disabled={resetPassword.isPending}
                  className="pr-10"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-0 top-0 h-full px-3 hover:bg-transparent"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                >
                  {showConfirmPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </Button>
              </div>
              {confirmPassword && password !== confirmPassword && (
                <p className="text-xs text-destructive flex items-center gap-1">
                  <AlertCircle className="h-3 w-3" />
                  Passwords do not match
                </p>
              )}
            </div>

            <div className="rounded-lg bg-muted p-3 space-y-1">
              <p className="text-xs font-medium">Password requirements:</p>
              <ul className="text-xs text-muted-foreground space-y-0.5">
                <li className={password.length >= 8 ? 'text-green-600' : ''}>
                  • At least 8 characters
                </li>
                <li className={password.match(/[A-Z]/) ? 'text-green-600' : ''}>
                  • One uppercase letter
                </li>
                <li className={password.match(/[a-z]/) ? 'text-green-600' : ''}>
                  • One lowercase letter
                </li>
                <li className={password.match(/\d/) ? 'text-green-600' : ''}>
                  • One number
                </li>
              </ul>
            </div>
          </CardContent>
          <CardFooter>
            <Button 
              type="submit" 
              className="w-full gradient-primary"
              disabled={resetPassword.isPending || !password || !confirmPassword}
            >
              {resetPassword.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Resetting password...
                </>
              ) : (
                <>
                  <Lock className="mr-2 h-4 w-4" />
                  Reset password
                </>
              )}
            </Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}