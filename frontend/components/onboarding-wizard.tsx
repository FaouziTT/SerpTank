'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { 
  Building2, 
  Globe, 
  Link2, 
  Sparkles, 
  CheckCircle, 
  ArrowRight,
  Loader2,
  X,
  AlertCircle,
  ExternalLink,
  Zap,
  TrendingUp,
  BarChart3,
  Search,
  Shield,
  Brain,
  DollarSign,
  Activity
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { api, initializeCsrfToken } from '@/lib/api-client';
import { useAuth } from '@/lib/auth-context';
import { useProject } from '@/lib/project-context';
import { useToast } from '@/components/ui/use-toast';
import { cn } from '@/lib/utils';
import { SEOOrb } from '@/components/ui/seo-orb';

interface OnboardingData {
  organizationName: string;
  organizationDescription: string;
  projectName: string;
  websiteUrl: string;
  projectDescription: string;
  googleConnected: boolean;
  crawlStarted: boolean;
}

interface StepProps {
  data: OnboardingData;
  updateData: (updates: Partial<OnboardingData>) => void;
  onNext: () => void;
  onBack?: () => void;
}

const STEPS = [
  {
    id: 'welcome',
    title: 'Welcome to SerpTank SEO',
    icon: Sparkles,
    description: 'Let\'s get your SEO intelligence platform set up in just 3 minutes'
  },
  {
    id: 'organization',
    title: 'Create Your Organization',
    icon: Building2,
    description: 'Organizations help you manage multiple websites and collaborate with your team'
  },
  {
    id: 'project',
    title: 'Add Your First Website',
    icon: Globe,
    description: 'We\'ll analyze your website and start tracking its SEO performance'
  },
  {
    id: 'google',
    title: 'Connect Google Services',
    icon: Link2,
    description: 'Required: Link your Google account to access Search Console and Analytics data'
  },
  {
    id: 'complete',
    title: 'All Set!',
    icon: CheckCircle,
    description: 'Your SEO dashboard is ready. Let\'s explore your data!'
  }
];

// Step Components
function WelcomeStep({ onNext }: StepProps) {
  return (
    <div className="space-y-8">
      <motion.div 
        className="text-center space-y-4"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <div className="relative mx-auto w-32 h-32">
          {/* Mini SEO Orb behind the icon */}
          <motion.div 
            className="absolute inset-0 opacity-30"
            animate={{ 
              rotate: [0, 360],
            }}
            transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
          >
            <SEOOrb className="w-full h-full" colorTheme="neon" />
          </motion.div>
          
          {/* Icon container */}
          <motion.div 
            className="absolute inset-4 bg-gradient-to-br from-primary/20 to-accent/20 rounded-full flex items-center justify-center backdrop-blur-sm"
            animate={{ 
              boxShadow: ["0 0 20px rgba(59,130,246,0.3)", "0 0 40px rgba(59,130,246,0.5)", "0 0 20px rgba(59,130,246,0.3)"]
            }}
            transition={{ duration: 2, repeat: Infinity }}
          >
            <Sparkles className="h-10 w-10 text-primary relative z-10" />
          </motion.div>
        </div>
        <h2 className="text-3xl md:text-4xl font-bold tracking-tight">
          Welcome to <span className="text-gradient-electric">SerpTank SEO Platform</span>
        </h2>
        <p className="text-lg text-muted-foreground max-w-lg mx-auto leading-relaxed">
          Get actionable SEO insights, track your rankings, and optimize your content with AI-powered recommendations.
        </p>
      </motion.div>

      <div className="grid gap-4 sm:grid-cols-3">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          whileHover={{ y: -5, transition: { duration: 0.2 } }}
        >
          <Card className="border-primary/20 bg-gradient-to-br from-card/80 to-card/50 backdrop-blur-sm h-full relative overflow-hidden group">
            <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            <CardHeader className="pb-3 relative">
              <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-primary/10 to-primary/5 flex items-center justify-center mb-3 group-hover:scale-110 transition-transform duration-300">
                <BarChart3 className="h-8 w-8 text-primary" />
              </div>
              <CardTitle className="text-lg">Real-time Analytics</CardTitle>
            </CardHeader>
            <CardContent className="relative">
              <p className="text-sm text-muted-foreground">
                Monitor your SEO performance with live data from Google
              </p>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          whileHover={{ y: -5, transition: { duration: 0.2 } }}
        >
          <Card className="border-accent/20 bg-gradient-to-br from-card/80 to-card/50 backdrop-blur-sm h-full relative overflow-hidden group">
            <div className="absolute inset-0 bg-gradient-to-br from-accent/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            <CardHeader className="pb-3 relative">
              <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-accent/10 to-accent/5 flex items-center justify-center mb-3 group-hover:scale-110 transition-transform duration-300">
                <TrendingUp className="h-8 w-8 text-accent" />
              </div>
              <CardTitle className="text-lg">AI Insights</CardTitle>
            </CardHeader>
            <CardContent className="relative">
              <p className="text-sm text-muted-foreground">
                Get smart recommendations to improve your rankings
              </p>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          whileHover={{ y: -5, transition: { duration: 0.2 } }}
        >
          <Card className="border-purple-500/20 bg-gradient-to-br from-card/80 to-card/50 backdrop-blur-sm h-full relative overflow-hidden group">
            <div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            <CardHeader className="pb-3 relative">
              <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-purple-500/10 to-purple-500/5 flex items-center justify-center mb-3 group-hover:scale-110 transition-transform duration-300">
                <Search className="h-8 w-8 text-purple-500" />
              </div>
              <CardTitle className="text-lg">Competitor Analysis</CardTitle>
            </CardHeader>
            <CardContent className="relative">
              <p className="text-sm text-muted-foreground">
                Stay ahead by tracking your competition
              </p>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      <motion.div 
        className="flex justify-center pt-4"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.4 }}
      >
        <Button 
          size="lg" 
          onClick={onNext} 
          className="min-w-[200px] bg-gradient-to-r from-primary to-accent hover:from-primary/90 hover:to-accent/90 text-white shadow-lg shadow-primary/25 text-lg py-6"
        >
          Get Started
          <ArrowRight className="ml-2 h-5 w-5" />
        </Button>
      </motion.div>
    </div>
  );
}

function OrganizationStep({ data, updateData, onNext, onBack }: StepProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const validateAndContinue = async () => {
    if (!data.organizationName.trim()) {
      setError('Please enter an organization name');
      return;
    }

    setLoading(true);
    setError('');

    try {
      // Organization will be created in the final step
      onNext();
    } catch (err) {
      setError('Failed to validate organization name');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <div>
          <Label htmlFor="org-name">Organization Name *</Label>
          <Input
            id="org-name"
            placeholder="My Company"
            value={data.organizationName}
            onChange={(e) => {
              updateData({ organizationName: e.target.value });
              setError('');
            }}
            className={cn(error && 'border-destructive')}
          />
          {error && (
            <p className="text-sm text-destructive mt-1">{error}</p>
          )}
          <p className="text-sm text-muted-foreground mt-1">
            This is usually your company or agency name
          </p>
        </div>

        <div>
          <Label htmlFor="org-desc">Description (Optional)</Label>
          <Textarea
            id="org-desc"
            placeholder="Digital marketing agency focused on SEO..."
            value={data.organizationDescription}
            onChange={(e) => updateData({ organizationDescription: e.target.value })}
            rows={3}
          />
        </div>
      </div>

      <Alert>
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          You can invite team members and manage multiple websites under this organization later.
        </AlertDescription>
      </Alert>

      <div className="flex justify-between">
        <Button variant="outline" onClick={onBack}>
          Back
        </Button>
        <Button onClick={validateAndContinue} disabled={loading}>
          {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Continue
        </Button>
      </div>
    </div>
  );
}

function ProjectStep({ data, updateData, onNext, onBack }: StepProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [urlError, setUrlError] = useState('');

  const validateUrl = (url: string) => {
    if (!url) return 'Please enter a website URL';
    
    try {
      const urlObj = new URL(url);
      if (!['http:', 'https:'].includes(urlObj.protocol)) {
        return 'URL must start with http:// or https://';
      }
      return '';
    } catch {
      return 'Please enter a valid URL (e.g., https://example.com)';
    }
  };

  const validateAndContinue = async () => {
    const projectNameError = !data.projectName.trim() ? 'Please enter a project name' : '';
    const websiteUrlError = validateUrl(data.websiteUrl);

    if (projectNameError) setError(projectNameError);
    if (websiteUrlError) setUrlError(websiteUrlError);

    if (projectNameError || websiteUrlError) return;

    setLoading(true);
    setError('');
    setUrlError('');

    try {
      // Project will be created in the final step
      onNext();
    } catch (err) {
      setError('Failed to validate project details');
    } finally {
      setLoading(false);
    }
  };

  // Auto-fill project name from URL
  useEffect(() => {
    if (data.websiteUrl && !data.projectName) {
      try {
        const url = new URL(data.websiteUrl);
        const domain = url.hostname.replace('www.', '');
        updateData({ projectName: domain });
      } catch {
        // Invalid URL, ignore
      }
    }
  }, [data.websiteUrl, data.projectName, updateData]);

  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <div>
          <Label htmlFor="website-url">Website URL *</Label>
          <Input
            id="website-url"
            type="url"
            placeholder="https://example.com"
            value={data.websiteUrl}
            onChange={(e) => {
              updateData({ websiteUrl: e.target.value });
              setUrlError('');
            }}
            className={cn(urlError && 'border-destructive')}
          />
          {urlError && (
            <p className="text-sm text-destructive mt-1">{urlError}</p>
          )}
          <p className="text-sm text-muted-foreground mt-1">
            We&apos;ll analyze this website and track its SEO performance
          </p>
        </div>

        <div>
          <Label htmlFor="project-name">Project Name *</Label>
          <Input
            id="project-name"
            placeholder="My Website SEO"
            value={data.projectName}
            onChange={(e) => {
              updateData({ projectName: e.target.value });
              setError('');
            }}
            className={cn(error && 'border-destructive')}
          />
          {error && (
            <p className="text-sm text-destructive mt-1">{error}</p>
          )}
        </div>

        <div>
          <Label htmlFor="project-desc">Description (Optional)</Label>
          <Textarea
            id="project-desc"
            placeholder="Main company website, e-commerce platform..."
            value={data.projectDescription}
            onChange={(e) => updateData({ projectDescription: e.target.value })}
            rows={3}
          />
        </div>
      </div>

      <Card className="bg-primary/5 border-primary/20">
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Zap className="h-4 w-4" />
            What happens next?
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <p className="text-sm">After setup, we&apos;ll automatically:</p>
          <ul className="text-sm space-y-1 ml-4">
            <li>• Crawl your website to analyze SEO health</li>
            <li>• Check Core Web Vitals and page speed</li>
            <li>• Identify technical SEO issues</li>
            <li>• Start monitoring your search rankings</li>
          </ul>
        </CardContent>
      </Card>

      <div className="flex justify-between">
        <Button variant="outline" onClick={onBack}>
          Back
        </Button>
        <Button onClick={validateAndContinue} disabled={loading}>
          {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Continue
        </Button>
      </div>
    </div>
  );
}

function GoogleConnectionStep({ data, updateData, onNext, onBack }: StepProps) {
  const [loading, setLoading] = useState(false);
  const [isVerifyingOAuth, setIsVerifyingOAuth] = useState(false);
  const [showCompletePanel, setShowCompletePanel] = useState(false);
  const [searchConsoleConnected, setSearchConsoleConnected] = useState(false);
  const [analyticsConnected, setAnalyticsConnected] = useState(false);
  const { toast } = useToast();

  const checkGoogleStatus = useCallback(async (isInitialCheck = false) => {
    try {
      const response = await api.oauth.status();
      const requirements = response.data.project_creation_requirements;
      const searchConsoleStatus = requirements?.search_console?.valid || false;
      const analyticsStatus = requirements?.analytics?.valid || false;

      console.log('OAuth Status Check:', {
        search_console: searchConsoleStatus,
        analytics: analyticsStatus,
        allConnected: searchConsoleStatus && analyticsStatus
      });

      setSearchConsoleConnected(searchConsoleStatus);
      setAnalyticsConnected(analyticsStatus);

      const allConnected = searchConsoleStatus && analyticsStatus;
      updateData({ googleConnected: allConnected });

      if (allConnected) {
        console.log('All Google services connected! Stopping verification...');
        toast({
          title: 'All Set!',
          description: 'Both Google services connected successfully.',
        });
        setIsVerifyingOAuth(false); // This will stop the polling effect
        setShowCompletePanel(true); // Show the complete panel with manual continue button
      }
      // No 'else' here; let the polling continue if not connected
    } catch (error) {
      console.error('Failed to check OAuth status:', error);
      setIsVerifyingOAuth(false); // Stop on error
      toast({
        title: 'Error Checking Status',
        description: 'Could not verify the connection to Google. Please try again.',
        variant: 'destructive'
      });
    }
  }, [updateData, toast]);

  // Initial status check on component mount
  useEffect(() => {
    checkGoogleStatus();
  }, []);

  // Handle OAuth Return - Simplified callback detection only
  const searchParams = useSearchParams();

  // Effect 1: Handle OAuth callback detection (separate from polling)
  useEffect(() => {
    const oauthSuccess = searchParams.get('oauth_success');
    const oauthError = searchParams.get('oauth_error');

    if (oauthSuccess === 'true') {
      console.log('OAuth success detected, starting verification process...');

      toast({
        title: 'Google Account Linked!',
        description: 'Finalizing connection, this may take a moment...',
      });

      setIsVerifyingOAuth(true);

      // Clean up the URL
      const url = new URL(window.location.href);
      url.searchParams.delete('oauth_success');
      url.searchParams.delete('oauth_error');
      window.history.replaceState({}, document.title, url.toString());
    } else if (oauthError) {
      console.error('OAuth error detected:', oauthError);
      toast({
        title: 'OAuth Error',
        description: `Authentication failed: ${oauthError}`,
        variant: 'destructive',
      });
    }
  }, [searchParams, toast]);

  // Effect 2: State-driven polling mechanism
  useEffect(() => {
    if (isVerifyingOAuth) {
      console.log('Starting OAuth verification polling...');

      const interval = setInterval(() => {
        console.log('Polling OAuth status...');
        checkGoogleStatus();
      }, 3000);

      const timeout = setTimeout(() => {
        console.log('OAuth polling timeout reached');
        setIsVerifyingOAuth(false);
        toast({
          title: 'Connection Timeout',
          description: 'The connection is taking longer than expected. Please try again.',
          variant: 'destructive',
        });
      }, 30000); // 30-second timeout

      // Initial check after a brief delay
      const initialCheck = setTimeout(() => {
        console.log('Starting initial OAuth status check...');
        checkGoogleStatus(true);
      }, 2000);

      return () => {
        clearInterval(interval);
        clearTimeout(timeout);
        clearTimeout(initialCheck);
      };
    }
  }, [isVerifyingOAuth, checkGoogleStatus, toast]);

  const handleConnectBoth = async () => {
    if (loading) return;
    setLoading(true);
    try {
      const response = await api.oauth.google.authorize({ scopes: 'full' });
      sessionStorage.setItem('onboarding_data', JSON.stringify(data));
      sessionStorage.setItem('onboarding_step', 'google');
      window.location.href = response.data.authorization_url;
    } catch (error: any) {
      console.error('Google OAuth connection error:', error);
      
      let errorMessage = 'Failed to connect to Google. Please try again.';
      let errorTitle = 'Connection Failed';
      
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail;
        if (typeof detail === 'object' && detail.error === 'Google OAuth not configured') {
          errorTitle = 'OAuth Setup Required';
          errorMessage = `${detail.message} Please ask your administrator to configure Google OAuth credentials.`;
        } else if (typeof detail === 'string') {
          errorMessage = detail;
        }
      } else if (error.response?.status === 503) {
        errorTitle = 'Service Configuration Required';
        errorMessage = 'Google OAuth is not configured. Please contact your administrator to set up Google OAuth credentials.';
      }
      
      toast({
        title: errorTitle,
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  // Dedicated UI for the "Verifying" state
  if (isVerifyingOAuth) {
    return (
      <div className="flex flex-col items-center justify-center py-12 space-y-4">
        <Loader2 className="h-10 w-10 animate-spin text-primary" />
        <h3 className="text-lg font-semibold">Verifying Connection...</h3>
        <p className="text-muted-foreground text-center max-w-sm">
          This can sometimes take up to 30 seconds as we securely establish a link with your Google account.
        </p>
      </div>
    );
  }

  if (data.googleConnected) {
    return (
      <div className="space-y-6">
        <div className="text-center space-y-4">
          <div className="mx-auto w-16 h-16 bg-green-100 dark:bg-green-900/20 rounded-full flex items-center justify-center">
            <CheckCircle className="h-8 w-8 text-green-600" />
          </div>
          <h3 className="text-lg font-semibold">Google Account Connected!</h3>
          <p className="text-muted-foreground">
            You&apos;re all set to access powerful SEO insights and data.
          </p>
        </div>

        <Card className="border-green-200 bg-green-50/50 dark:bg-green-950/20">
          <CardContent className="pt-6 space-y-3">
            <h4 className="font-medium text-sm mb-3">You now have access to:</h4>
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-green-600" />
                <span className="text-sm">Real-time search performance metrics</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-green-600" />
                <span className="text-sm">Keyword rankings and click-through rates</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-green-600" />
                <span className="text-sm">User behavior and conversion tracking</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-green-600" />
                <span className="text-sm">Core Web Vitals monitoring</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="flex justify-between">
          <Button variant="outline" onClick={onBack}>
            Back
          </Button>
          <Button onClick={onNext} className="gap-2">
            Continue to Dashboard
            <ArrowRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <div className="text-center mb-6">
          <h3 className="text-lg font-semibold mb-2">Connect Google Services</h3>
          <p className="text-sm text-muted-foreground">
            <strong>Required:</strong> Connect your Google account to access Search Console and Analytics data for complete SEO insights
          </p>
        </div>

        <Card className="border-primary/20">
          <CardHeader className="pb-4">
            <CardTitle className="text-base flex items-center gap-2">
              <Globe className="h-5 w-5 text-primary" />
              Google Search Console
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex items-start gap-2">
              <CheckCircle className="h-4 w-4 text-green-500 mt-0.5" />
              <div>
                <p className="text-sm font-medium">Track Real Search Performance</p>
                <p className="text-xs text-muted-foreground">
                  See exact queries driving traffic, click-through rates, and average positions
                </p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <CheckCircle className="h-4 w-4 text-green-500 mt-0.5" />
              <div>
                <p className="text-sm font-medium">Discover Keyword Opportunities</p>
                <p className="text-xs text-muted-foreground">
                  Find high-impression, low-click keywords you can optimize for quick wins
                </p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <CheckCircle className="h-4 w-4 text-green-500 mt-0.5" />
              <div>
                <p className="text-sm font-medium">Monitor Indexing Status</p>
                <p className="text-xs text-muted-foreground">
                  Get alerts about crawl errors and indexing issues before they impact rankings
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-primary/20">
          <CardHeader className="pb-4">
            <CardTitle className="text-base flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-primary" />
              Google Analytics 4
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex items-start gap-2">
              <CheckCircle className="h-4 w-4 text-green-500 mt-0.5" />
              <div>
                <p className="text-sm font-medium">Measure ROI & Conversions</p>
                <p className="text-xs text-muted-foreground">
                  Track revenue from organic traffic and calculate true SEO ROI
                </p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <CheckCircle className="h-4 w-4 text-green-500 mt-0.5" />
              <div>
                <p className="text-sm font-medium">Understand User Behavior</p>
                <p className="text-xs text-muted-foreground">
                  See how visitors interact with your content and optimize for engagement
                </p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <CheckCircle className="h-4 w-4 text-green-500 mt-0.5" />
              <div>
                <p className="text-sm font-medium">Content Performance Insights</p>
                <p className="text-xs text-muted-foreground">
                  Identify your best-performing pages and replicate their success
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Alert className="border-red-200 bg-red-50/50 dark:bg-red-950/20">
          <AlertCircle className="h-4 w-4 text-red-600" />
          <AlertDescription className="text-red-800 dark:text-red-200">
            <strong>Required:</strong> Google connection is mandatory to proceed. This ensures you get complete SEO insights and performance tracking for your website.
          </AlertDescription>
        </Alert>

        <Alert className="border-green-200 bg-green-50 dark:bg-green-950/20">
          <TrendingUp className="h-4 w-4 text-green-600" />
          <AlertDescription className="text-green-800 dark:text-green-200">
            <strong>Did you know?</strong> Sites using our Google integrations see an average 
            <strong className="mx-1">47% increase</strong> in organic traffic within 3 months.
          </AlertDescription>
        </Alert>

        <Alert>
          <Shield className="h-4 w-4" />
          <AlertDescription>
            <strong>Secure:</strong> We only request read-only access and use industry-standard encryption. Your data is never stored or shared with third parties.
          </AlertDescription>
        </Alert>
      </div>

      <div className="space-y-6">
        {/* Connection Status Display */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card className={cn(
            "p-4",
            searchConsoleConnected ? "border-green-200 bg-green-50/50 dark:bg-green-950/20" : "border-muted"
          )}>
            <div className="flex items-center gap-3">
              {searchConsoleConnected ? (
                <CheckCircle className="h-6 w-6 text-green-600" />
              ) : (
                <Search className="h-6 w-6 text-muted-foreground" />
              )}
              <div>
                <h4 className="font-medium text-sm">
                  {searchConsoleConnected ? 'Search Console Connected' : 'Search Console'}
                </h4>
                <p className="text-xs text-muted-foreground">
                  {searchConsoleConnected ? 'Ready to track search performance' : 'Track search performance and keyword rankings'}
                </p>
              </div>
            </div>
          </Card>

          <Card className={cn(
            "p-4",
            analyticsConnected ? "border-green-200 bg-green-50/50 dark:bg-green-950/20" : "border-muted"
          )}>
            <div className="flex items-center gap-3">
              {analyticsConnected ? (
                <CheckCircle className="h-6 w-6 text-green-600" />
              ) : (
                <BarChart3 className="h-6 w-6 text-muted-foreground" />
              )}
              <div>
                <h4 className="font-medium text-sm">
                  {analyticsConnected ? 'Analytics Connected' : 'Google Analytics'}
                </h4>
                <p className="text-xs text-muted-foreground">
                  {analyticsConnected ? 'Ready to track conversions and behavior' : 'Track traffic, conversions, and user behavior'}
                </p>
              </div>
            </div>
          </Card>
        </div>

        {/* Connect both services button */}
        {!searchConsoleConnected || !analyticsConnected ? (
          <div className="text-center">
            <Button 
              onClick={handleConnectBoth} 
              disabled={loading} 
              size="lg" 
              className="w-full max-w-md"
            >
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Connect Google Services
              <ExternalLink className="ml-2 h-4 w-4" />
            </Button>
            <p className="text-xs text-muted-foreground mt-2">
              This will connect both Search Console and Analytics in one step
            </p>
          </div>
        ) : null}

        {/* Navigation buttons */}
        <div className="flex items-center justify-between pt-4">
          <Button variant="outline" onClick={onBack}>
            Back
          </Button>
          {searchConsoleConnected && analyticsConnected && (
            <Button onClick={onNext} className="gap-2">
              Continue to Dashboard
              <ArrowRight className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

function CrawlLoadingScreen({ projectId }: { projectId: number }) {
  const [analysisStatus, setAnalysisStatus] = useState<any>(null);
  const [progress, setProgress] = useState(0);
  const [completedTasks, setCompletedTasks] = useState<string[]>([]);
  const [isGrandFinale, setIsGrandFinale] = useState(false);
  const [particles, setParticles] = useState<Array<{ id: string; from: string; startX: number; startY: number; endX: number; endY: number }>>([]);
  const taskRefs = useRef<{ [key: string]: HTMLDivElement | null }>({});
  const orbRef = useRef<HTMLDivElement | null>(null);
  const router = useRouter();

  console.log('CrawlLoadingScreen rendered with projectId:', projectId);

  // Helper function to calculate particle path coordinates
  const calculateParticleCoordinates = (taskName: string) => {
    const taskElement = taskRefs.current[taskName];
    const orbElement = orbRef.current;
    
    if (!taskElement || !orbElement) {
      // Fallback to approximate positions
      return {
        startX: 20, // 20% from left (task area)
        startY: 60, // 60% from top (task area)
        endX: 50,   // 50% from left (orb center)
        endY: 20    // 20% from top (orb center)
      };
    }

    const taskRect = taskElement.getBoundingClientRect();
    const orbRect = orbElement.getBoundingClientRect();
    const containerRect = taskElement.closest('.space-y-8')?.getBoundingClientRect();
    
    if (!containerRect) {
      return {
        startX: 20, startY: 60, endX: 50, endY: 20
      };
    }

    // Calculate positions as percentages relative to the container
    const startX = ((taskRect.right - containerRect.left) / containerRect.width) * 100;
    const startY = ((taskRect.top + taskRect.height / 2 - containerRect.top) / containerRect.height) * 100;
    const endX = ((orbRect.left + orbRect.width / 2 - containerRect.left) / containerRect.width) * 100;
    const endY = ((orbRect.top + orbRect.height / 2 - containerRect.top) / containerRect.height) * 100;

    return { startX, startY, endX, endY };
  };

  useEffect(() => {
    let interval: NodeJS.Timeout;

    const checkAnalysisStatus = async () => {
    try {
      console.log('Making analysis status request for project ID:', projectId);
      const response = await api.projects.getAnalysisStatus(String(projectId));
      const status = response.data;
      console.log('Analysis status response:', status);
      
      // Use the new backend response format with detailed progress
      const transformedTasks: { [key: string]: { status: string; message: string; progress: number } } = {};

      // Website Crawl task
      if (status.tasks?.crawl) {
        transformedTasks['Website Crawl'] = {
          status: status.tasks.crawl.status === 'completed' ? 'completed' :
                  status.tasks.crawl.status === 'in_progress' ? 'in_progress' : 'pending',
          message: status.tasks.crawl.message || 'Processing website crawl...',
          progress: status.tasks.crawl.progress || 0
        };
      } else {
        // Fallback for old format
        transformedTasks['Website Crawl'] = {
          status: status.crawl_status === 'completed' ? 'completed' :
                  status.crawl_status === 'pending' ? 'pending' : 'in_progress',
          message: status.crawl_status === 'completed' ? 'Crawling completed successfully' :
                  status.crawl_status === 'pending' ? 'Starting website crawl...' : 'Crawling your website...',
          progress: status.crawl_status === 'completed' ? 100 :
                   status.crawl_status === 'pending' ? 0 : 50
        };
      }

      // Core Web Vitals task
      if (status.tasks?.cwv) {
        transformedTasks['Core Web Vitals'] = {
          status: status.tasks.cwv.status === 'completed' ? 'completed' :
                  status.tasks.cwv.status === 'in_progress' ? 'in_progress' :
                  status.tasks.cwv.status === 'not_configured' ? 'completed' : 'pending',
          message: status.tasks.cwv.message || 'Processing performance analysis...',
          progress: status.tasks.cwv.progress || 0
        };
      } else {
        // Fallback for old format
        transformedTasks['Core Web Vitals'] = {
          status: status.cwv_status === 'completed' ? 'completed' :
                  status.cwv_status === 'not_configured' ? 'completed' :
                  status.cwv_status === 'pending' ? 'pending' : 'in_progress',
          message: status.cwv_status === 'completed' ? 'Performance analysis completed' :
                   status.cwv_status === 'not_configured' ? 'Skipped (not configured)' :
                   status.cwv_status === 'pending' ? 'Starting performance analysis...' : 'Analyzing website performance...',
          progress: status.cwv_status === 'completed' || status.cwv_status === 'not_configured' ? 100 :
                   status.cwv_status === 'pending' ? 0 : 50
        };
      }

      // Revenue analysis task (only if configured)
      if (status.tasks?.revenue && status.profitability_status !== 'not_configured') {
        transformedTasks['Profitability Analysis'] = {
          status: status.tasks.revenue.status === 'completed' ? 'completed' :
                  status.tasks.revenue.status === 'in_progress' ? 'in_progress' : 'pending',
          message: status.tasks.revenue.message || 'Processing revenue analysis...',
          progress: status.tasks.revenue.progress || 0
        };
      } else if (status.profitability_status !== 'not_configured') {
        // Fallback for old format
        transformedTasks['Profitability Analysis'] = {
          status: status.profitability_status === 'completed' ? 'completed' :
                  status.profitability_status === 'pending' ? 'pending' : 'in_progress',
          message: status.profitability_status === 'completed' ? 'Revenue analysis completed' :
                   status.profitability_status === 'pending' ? 'Starting revenue analysis...' : 'Analyzing revenue data...',
          progress: status.profitability_status === 'completed' ? 100 :
                   status.profitability_status === 'pending' ? 0 : 50
        };
      }

      setAnalysisStatus(transformedTasks);

      // Detect newly completed tasks for particle animations
      const currentlyCompletedTasks = Object.entries(transformedTasks)
        .filter(([_, task]: [string, any]) => task.status === 'completed')
        .map(([taskName, _]) => taskName);

      // Check for new completions
      const newlyCompleted = currentlyCompletedTasks.filter(
        taskName => !completedTasks.includes(taskName)
      );

      // Trigger particle animations for newly completed tasks
      if (newlyCompleted.length > 0) {
        console.log('Newly completed tasks:', newlyCompleted);
        const newParticles = newlyCompleted.map(taskName => {
          const coords = calculateParticleCoordinates(taskName);
          return {
            id: `${taskName}-${Date.now()}`,
            from: taskName,
            startX: coords.startX,
            startY: coords.startY,
            endX: coords.endX,
            endY: coords.endY
          };
        });
        setParticles(prev => [...prev, ...newParticles]);
        setCompletedTasks(currentlyCompletedTasks);

        // Remove particles after animation completes
        setTimeout(() => {
          setParticles(prev => prev.filter(p => !newParticles.some(np => np.id === p.id)));
        }, 2000);
      }

      // Use backend-calculated overall progress if available, otherwise calculate from tasks
      let currentProgress;
      if (status.overall_progress !== undefined) {
        currentProgress = Math.round(status.overall_progress);
      } else {
        // Fallback: calculate from individual tasks
        let totalProgress = 0;
        const taskValues = Object.values(transformedTasks);
        taskValues.forEach(task => {
          totalProgress += task.progress;
        });
        currentProgress = Math.round(totalProgress / taskValues.length);
      }

      setProgress(prevProgress => {
        // Only update progress if it's moving forward, preventing flicker
        return currentProgress > prevProgress ? currentProgress : prevProgress;
      });

      console.log('Current progress:', currentProgress, 'Overall status:', status.overall_status);

      // Trigger grand finale when all tasks are complete
      if (status.overall_status === 'complete' && !isGrandFinale) {
        console.log('All analysis tasks completed, starting grand finale');
        setProgress(100); // Ensure it hits 100% before grand finale
        setIsGrandFinale(true);
        clearInterval(interval);
        
        // Start grand finale sequence
        setTimeout(() => {
          console.log('Grand finale complete, redirecting to dashboard');
          router.push('/dashboard');
        }, 3500); // Give time for the grand finale animation
      }
    } catch (error) {
      console.error('Failed to check analysis status:', error);
      clearInterval(interval);
      setTimeout(() => {
        console.log('Redirecting to dashboard due to API error');
        router.push('/dashboard');
      }, 10000);
    }
  };

    // Check status immediately and then every 2 seconds
    console.log('Starting analysis status polling for project:', projectId);
    checkAnalysisStatus();
    interval = setInterval(() => {
      console.log('Interval tick - checking status again...');
      checkAnalysisStatus();
    }, 2000);

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [projectId, router]);

  return (
    <div className="space-y-8 relative">
      {/* Grand Finale Overlay */}
      <AnimatePresence>
        {isGrandFinale && (
          <motion.div
            className="fixed inset-0 z-50 bg-background flex items-center justify-center"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
          >
            <motion.div
              className="w-96 h-96"
              initial={{ scale: 1 }}
              animate={{ 
                scale: [1, 1.2, 6],
                rotate: [0, 180, 360],
                opacity: [1, 1, 0]
              }}
              transition={{ 
                duration: 3,
                times: [0, 0.6, 1],
                ease: "easeInOut"
              }}
            >
              <img
                src="/serptank-orb-logo.svg"
                alt="SerpTank Orb"
                className="w-full h-full"
              />
            </motion.div>
            {/* Multi-layered colored fade finale */}
            <motion.div
              className="absolute inset-0 bg-gradient-radial from-blue-500/30 via-purple-500/20 to-transparent"
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 4, opacity: [0, 0.8, 0] }}
              transition={{ delay: 0.8, duration: 2.2, ease: "easeOut" }}
            />
            <motion.div
              className="absolute inset-0 bg-gradient-radial from-primary/40 via-accent/25 to-emerald-400/10"
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 3, opacity: [0, 1, 0.3] }}
              transition={{ delay: 1, duration: 1.8, ease: "easeInOut" }}
            />
            <motion.div
              className="absolute inset-0 bg-gradient-conic from-primary via-accent to-purple-500"
              initial={{ scale: 0, opacity: 0, rotate: 0 }}
              animate={{ scale: 2, opacity: [0, 0.6, 0], rotate: 180 }}
              transition={{ delay: 1.5, duration: 1.5, ease: "easeOut" }}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Particle System */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <AnimatePresence>
          {particles.map((particle) => (
            <motion.div
              key={particle.id}
              className="absolute w-3 h-3 bg-gradient-to-r from-primary to-accent rounded-full shadow-lg"
              initial={{ 
                left: `${particle.startX}%`, 
                top: `${particle.startY}%`,
                scale: 0,
                opacity: 0
              }}
              animate={{ 
                left: `${particle.endX}%`, 
                top: `${particle.endY}%`,
                scale: [0, 1.2, 0.8, 0],
                opacity: [0, 1, 1, 0]
              }}
              exit={{ opacity: 0 }}
              transition={{ 
                duration: 1.8,
                ease: "easeOut",
                scale: {
                  times: [0, 0.3, 0.8, 1],
                  ease: ["easeOut", "easeInOut", "easeIn"]
                }
              }}
            >
              {/* Add a glowing trail effect */}
              <motion.div
                className="absolute inset-0 bg-gradient-to-r from-primary/60 to-accent/60 rounded-full blur-sm"
                animate={{
                  scale: [1, 1.5, 1]
                }}
                transition={{
                  duration: 0.5,
                  repeat: Infinity,
                  ease: "easeInOut"
                }}
              />
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      <div className="text-center space-y-4 relative z-10">
        {/* The Beginning: Enhanced SEOOrb with Thinking Animation */}
        <motion.div
          className="relative mx-auto w-32 h-32"
          animate={{
            scale: progress < 100 ? [1, 1.05, 1] : 1,
          }}
          transition={{
            duration: 2,
            repeat: progress < 100 ? Infinity : 0,
            ease: "easeInOut"
          }}
        >
          {/* Thinking pulse layers with SerpTank logo */}
          {progress < 100 && (
            <>
              {/* Outer pulsing logo layer */}
              <motion.div
                className="absolute inset-0 opacity-20"
                animate={{
                  scale: [1, 1.8, 2.2],
                  opacity: [0.3, 0.15, 0]
                }}
                transition={{
                  duration: 2.5,
                  repeat: Infinity,
                  ease: "easeOut"
                }}
              >
                <img
                  src="/serptank-orb-logo.svg"
                  alt="SerpTank Orb"
                  className="w-full h-full"
                />
              </motion.div>

              {/* Middle pulsing logo layer */}
              <motion.div
                className="absolute inset-0 opacity-30"
                animate={{
                  scale: [1, 1.4, 1.8],
                  opacity: [0.4, 0.2, 0]
                }}
                transition={{
                  duration: 2,
                  repeat: Infinity,
                  ease: "easeOut",
                  delay: 0.3
                }}
              >
                <img
                  src="/serptank-orb-logo.svg"
                  alt="SerpTank Orb"
                  className="w-full h-full"
                />
              </motion.div>

              {/* Inner pulsing logo layer */}
              <motion.div
                className="absolute inset-0 opacity-40"
                animate={{
                  scale: [1, 1.2, 1.5],
                  opacity: [0.5, 0.3, 0]
                }}
                transition={{
                  duration: 1.8,
                  repeat: Infinity,
                  ease: "easeOut",
                  delay: 0.6
                }}
              >
                <img
                  src="/serptank-orb-logo.svg"
                  alt="SerpTank Orb"
                  className="w-full h-full"
                />
              </motion.div>
            </>
          )}
          
          {/* Main SerpTank Logo */}
          <motion.div
            ref={orbRef}
            className="relative z-10"
            animate={{
              rotate: [0, 360],
              filter: progress < 100
                ? ["brightness(1) saturate(1)", "brightness(1.2) saturate(1.1)", "brightness(1) saturate(1)"]
                : ["brightness(1.5) saturate(1.2)"]
            }}
            transition={{
              rotate: { duration: 20, repeat: Infinity, ease: "linear" },
              filter: { duration: 3, repeat: progress < 100 ? Infinity : 0, ease: "easeInOut" }
            }}
          >
            <img
              src="/serptank-orb-logo.svg"
              alt="SerpTank Orb"
              className="w-full h-full"
            />
          </motion.div>

          {/* Intelligence gathering effect */}
          {progress > 0 && progress < 100 && (
            <motion.div
              className="absolute inset-2 bg-gradient-to-r from-primary/20 to-accent/20 rounded-full"
              animate={{
                opacity: [0, 0.3, 0],
                scale: [0.8, 1.1, 0.8]
              }}
              transition={{
                duration: 1.5,
                repeat: Infinity,
                ease: "easeInOut"
              }}
            />
          )}
        </motion.div>

        <motion.h3 
          className="text-xl font-semibold"
          animate={{
            color: progress >= 100 ? ["#ffffff", "#3b82f6", "#8b5cf6"] : "#ffffff"
          }}
          transition={{
            duration: 2,
            repeat: progress >= 100 ? Infinity : 0
          }}
        >
          {progress >= 100 ? "Analysis Complete!" : "Analyzing Your Website"}
        </motion.h3>
        
        <motion.p 
          className="text-muted-foreground max-w-md mx-auto"
          animate={{
            opacity: progress >= 100 ? [1, 0.7, 1] : 1
          }}
          transition={{
            duration: 1.5,
            repeat: progress >= 100 ? Infinity : 0
          }}
        >
          {progress >= 100 
            ? "Preparing your personalized SEO dashboard..." 
            : "We're crawling your website and analyzing its SEO performance. This will take a few minutes."
          }
        </motion.p>
      </div>

      <div className="space-y-6 max-w-md mx-auto relative z-10">
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span>Overall Progress</span>
            <span>{progress}%</span>
          </div>
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <Progress value={progress} className="h-2" />
          </motion.div>
        </div>

        {analysisStatus && (
          <motion.div 
            className="space-y-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            <h4 className="font-medium">Analysis Tasks</h4>
            <div className="space-y-3">
              {Object.entries(analysisStatus).map(([taskName, task]: [string, any], index) => (
                <motion.div 
                  key={taskName} 
                  ref={(el) => { taskRefs.current[taskName] = el; }}
                  className="flex items-center justify-between p-3 bg-muted/50 rounded-lg relative overflow-hidden"
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.5, delay: index * 0.1 }}
                  whileHover={{ scale: 1.02 }}
                >
                  {/* Task completion celebration effect */}
                  {task.status === 'completed' && (
                    <motion.div
                      className="absolute inset-0 bg-gradient-to-r from-green-500/20 to-emerald-500/20"
                      initial={{ opacity: 0, scale: 0.8 }}
                      animate={{ opacity: [0, 0.5, 0], scale: [0.8, 1.1, 1] }}
                      transition={{ duration: 1.5 }}
                    />
                  )}
                  
                  <div className="flex items-center space-x-3 relative z-10">
                    <motion.div
                      animate={{
                        scale: task.status === 'completed' ? [1, 1.2, 1] : 1,
                        rotate: task.status === 'in_progress' ? [0, 360] : 0
                      }}
                      transition={{
                        scale: { duration: 0.6 },
                        rotate: { duration: 2, repeat: task.status === 'in_progress' ? Infinity : 0, ease: "linear" }
                      }}
                    >
                      {task.status === 'completed' ? (
                        <CheckCircle className="h-5 w-5 text-green-600" />
                      ) : task.status === 'in_progress' ? (
                        <Loader2 className="h-5 w-5 animate-spin text-primary" />
                      ) : (
                        <div className="h-5 w-5 rounded-full border-2 border-muted-foreground/30" />
                      )}
                    </motion.div>
                    <div>
                      <p className="font-medium text-sm capitalize">
                        {taskName.replace(/_/g, ' ')}
                      </p>
                      {task.message && (
                        <motion.p 
                          className="text-xs text-muted-foreground"
                          key={task.message}
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          transition={{ duration: 0.3 }}
                        >
                          {task.message}
                        </motion.p>
                      )}
                    </div>
                  </div>
                  {task.progress > 0 && task.status !== 'completed' && (
                    <motion.div
                      initial={{ opacity: 0, scale: 0.8 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ duration: 0.3 }}
                    >
                      <Badge variant="outline" className="text-xs">
                        {task.progress}%
                      </Badge>
                    </motion.div>
                  )}
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}

        <motion.div 
          className="text-center"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8, duration: 0.5 }}
        >
          <p className="text-xs text-muted-foreground">
            You can close this page and come back later - your analysis will continue in the background.
          </p>
        </motion.div>
      </div>
    </div>
  );
}

function CompleteStep({ data, updateData, onNext }: StepProps) {
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [projectId, setProjectId] = useState<number | null>(null);
  const router = useRouter();
  const { toast } = useToast();
  const { refetch } = useProject();

  const createResources = useCallback(async () => {
    // Prevent multiple executions
    if (creating) {
      console.log('Creation already in progress, skipping...');
      return;
    }

    console.log('Starting resource creation...');
    setCreating(true);
    setError(null);

    try {
      // Validate Google connection before proceeding
      if (!data.googleConnected) {
        throw new Error('Google connection is required to complete setup. Please go back and connect your Google account.');
      }

      console.log('Getting fresh CSRF token...');
      // Ensure fresh CSRF token is available
      await initializeCsrfToken();

      console.log('Creating organization...');
      // Create organization
      const orgResponse = await api.organizations.create({
        name: data.organizationName,
        description: data.organizationDescription || undefined,
      });

      console.log('Organization created:', orgResponse.data.id);

      // Wait a moment and get fresh CSRF token before project creation
      console.log('Waiting and refreshing CSRF token...');
      await new Promise(resolve => setTimeout(resolve, 300));
      await initializeCsrfToken();

      console.log('Creating project...');
      // Create project with initial analysis options
      const projectResponse = await api.projects.create({
        name: data.projectName,
        url: data.websiteUrl,
        description: data.projectDescription || undefined,
        organization_id: orgResponse.data.id,
        run_initial_crawl: true, // Always run initial crawl
        run_initial_core_web_vitals: true, // Always analyze Core Web Vitals
      });

      console.log('Project created:', projectResponse.data.id);

      // Store project ID for loading screen
      setProjectId(projectResponse.data.id);

      // Mark crawl as started for loading screen
      updateData({ crawlStarted: true });

      // Refresh project context
      await refetch();

      console.log('Marking onboarding as complete...');
      // Mark onboarding as complete with retry logic
      let retries = 3;
      while (retries > 0) {
        try {
          await api.auth.completeOnboarding();
          console.log('Onboarding marked as complete');
          break;
        } catch (completeError) {
          console.error(`Failed to mark onboarding as complete (${4 - retries}/3):`, completeError);
          retries--;
          if (retries > 0) {
            console.log('Retrying in 1 second...');
            await new Promise(resolve => setTimeout(resolve, 1000));
          }
        }
      }

      // Clear onboarding data
      sessionStorage.removeItem('onboarding_data');
      sessionStorage.removeItem('onboarding_step');

      toast({
        title: 'Setup complete!',
        description: 'Analyzing your website now...',
      });

      // Don't redirect immediately - let the loading screen handle it
      console.log('Project setup complete, crawl started');

    } catch (error: any) {
      console.error('Failed to create resources:', error);
      
      // Extract detailed error message
      let errorMessage = 'There was an error setting up your account. Please try again.';
      
      if (error.response) {
        console.error('Error response:', error.response);
        if (error.response.data) {
          if (error.response.data.detail) {
            errorMessage = error.response.data.detail;
          } else if (error.response.data.message) {
            errorMessage = error.response.data.message;
          } else if (error.response.data.error?.message) {
            errorMessage = error.response.data.error.message;
          }
        }
        
        // If organization already exists, just redirect to dashboard
        if (error.response.status === 400 && errorMessage.includes('already have an organization')) {
          toast({
            title: 'Organization exists',
            description: 'Redirecting to your dashboard...',
          });
          
          // Refresh project context and redirect
          await refetch();
          setTimeout(() => {
            router.push('/dashboard');
          }, 1000);
          return;
        }
      } else if (error.request) {
        console.error('No response received:', error.request);
        errorMessage = 'No response from server. Please check your connection.';
      } else {
        console.error('Error message:', error.message);
        errorMessage = error.message || errorMessage;
      }
      
      setError(errorMessage);
      toast({
        title: 'Setup failed',
        description: errorMessage,
        variant: 'destructive',
      });
      setCreating(false);
    }
  }, [creating, data, toast, router, refetch]);

  // Use a ref to ensure single execution
  const hasExecuted = useRef(false);

  useEffect(() => {
    if (!hasExecuted.current && !creating) {
      hasExecuted.current = true;
      console.log('CompleteStep mounted, starting creation...');
      createResources();
    }
  }, [createResources, creating]);

  // Show crawl loading screen after project creation
  if (data.crawlStarted && projectId) {
    return <CrawlLoadingScreen projectId={projectId} />;
  }

  return (
    <div className="space-y-6">
      <div className="text-center space-y-4">
        {creating ? (
          <>
            <Loader2 className="h-12 w-12 animate-spin mx-auto text-primary" />
            <h3 className="text-lg font-semibold">Setting up your dashboard...</h3>
            <p className="text-muted-foreground">
              This will just take a moment
            </p>
          </>
        ) : error ? (
          <>
            <div className="mx-auto w-16 h-16 bg-red-100 dark:bg-red-900/20 rounded-full flex items-center justify-center">
              <AlertCircle className="h-8 w-8 text-red-600" />
            </div>
            <h3 className="text-lg font-semibold">Setup Failed</h3>
            <p className="text-muted-foreground">
              {error}
            </p>
            <Button onClick={() => {
              setError(null);
              hasExecuted.current = false;
              createResources();
            }}>
              Try Again
            </Button>
          </>
        ) : (
          <>
            <div className="mx-auto w-16 h-16 bg-green-100 dark:bg-green-900/20 rounded-full flex items-center justify-center">
              <CheckCircle className="h-8 w-8 text-green-600" />
            </div>
            <h3 className="text-lg font-semibold">You&apos;re all set!</h3>
            <p className="text-muted-foreground">
              Redirecting to your dashboard...
            </p>
          </>
        )}
      </div>

      <Card className="bg-primary/5 border-primary/20">
        <CardHeader className="pb-3">
          <CardTitle className="text-base">What&apos;s happening now?</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <div className={cn(
                "h-2 w-2 rounded-full",
                creating ? "bg-yellow-500 animate-pulse" : "bg-green-500"
              )} />
              <span className="text-sm">Creating your organization</span>
            </div>
            <div className="flex items-center gap-3">
              <div className={cn(
                "h-2 w-2 rounded-full",
                creating ? "bg-yellow-500 animate-pulse" : "bg-green-500"
              )} />
              <span className="text-sm">Setting up your first project</span>
            </div>
            <div className="flex items-center gap-3">
              <div className={cn(
                "h-2 w-2 rounded-full",
                creating ? "bg-muted" : "bg-green-500"
              )} />
              <span className="text-sm">Starting website analysis</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export function OnboardingWizard() {
  const [currentStep, setCurrentStep] = useState(0);
  const [data, setData] = useState<OnboardingData>({
    organizationName: '',
    organizationDescription: '',
    projectName: '',
    websiteUrl: '',
    projectDescription: '',
    googleConnected: false,
    crawlStarted: false,
  });

  // Check if returning from Google OAuth
  useEffect(() => {
    const savedData = sessionStorage.getItem('onboarding_data');
    const savedStep = sessionStorage.getItem('onboarding_step');

    if (savedData && savedStep === 'google') {
      setData(JSON.parse(savedData));
      setCurrentStep(3); // Google connection step

      // Don't clean URL parameters here - let GoogleConnectionStep handle OAuth detection
      // This prevents race conditions where URL params are cleaned before detection
    }
  }, []);

  const updateData = (updates: Partial<OnboardingData>) => {
    setData(prev => ({ ...prev, ...updates }));
  };

  // Import useCallback at the top of the file if it's not already there
// import React, { useState, useEffect, useCallback } from 'react';

const goNext = useCallback(() => {
  if (currentStep < STEPS.length - 1) {
    setCurrentStep(currentStep + 1);
  }
}, [currentStep]); // The dependency is currentStep

const goBack = useCallback(() => {
  if (currentStep > 0) {
    setCurrentStep(currentStep - 1);
  }
}, [currentStep]); // The dependency is currentStep

  const progress = ((currentStep + 1) / STEPS.length) * 100;
  const currentStepInfo = STEPS[currentStep];

  const renderStep = () => {
    switch (currentStep) {
      case 0:
        return <WelcomeStep data={data} updateData={updateData} onNext={goNext} />;
      case 1:
        return <OrganizationStep data={data} updateData={updateData} onNext={goNext} onBack={goBack} />;
      case 2:
        return <ProjectStep data={data} updateData={updateData} onNext={goNext} onBack={goBack} />;
      case 3:
        return <GoogleConnectionStep data={data} updateData={updateData} onNext={goNext} onBack={goBack} />;
      case 4:
        return <CompleteStep data={data} updateData={updateData} onNext={goNext} />;
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-background relative overflow-hidden noise-overlay">
      {/* Background gradient mesh */}
      <div className="absolute inset-0 gradient-mesh opacity-20 dark:opacity-10" />
      
      {/* Animated background elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <motion.div
          className="absolute -top-32 -left-32 w-64 h-64 bg-primary/20 rounded-full blur-3xl"
          animate={{
            x: [0, 100, 0],
            y: [0, -50, 0],
          }}
          transition={{
            duration: 20,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />
        <motion.div
          className="absolute -bottom-32 -right-32 w-96 h-96 bg-accent/20 rounded-full blur-3xl"
          animate={{
            x: [0, -100, 0],
            y: [0, 50, 0],
          }}
          transition={{
            duration: 25,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />
        
        {/* SEO Orb - signature element */}
        <motion.div
          className="absolute right-[-300px] top-[20%] w-[600px] h-[600px] opacity-20 dark:opacity-10"
          animate={{
            y: [0, 30, 0],
            rotate: [0, 5, 0],
          }}
          transition={{
            duration: 15,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        >
          <SEOOrb className="w-full h-full" colorTheme="electric" />
        </motion.div>
      </div>
      
      <div className="container max-w-4xl mx-auto py-8 px-4 relative z-10">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-6">
            <motion.h1 
              className="text-4xl md:text-5xl font-bold tracking-tighter"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
            >
              Setup Your <span className="text-gradient-electric">SEO Dashboard</span>
            </motion.h1>
            {currentStep > 0 && currentStep < 4 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  if (confirm('Are you sure you want to exit setup? You can complete it later from settings.')) {
                    window.location.href = '/dashboard';
                  }
                }}
              >
                <X className="h-4 w-4 mr-1" />
                Exit Setup
              </Button>
            )}
          </div>
          
          {/* Progress bar with gradient */}
          <motion.div 
            className="space-y-2"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
          >
            <div className="relative h-3 bg-muted/30 rounded-full overflow-hidden backdrop-blur-sm">
              <motion.div 
                className="absolute inset-y-0 left-0 bg-gradient-to-r from-primary via-accent to-primary rounded-full"
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.8, ease: "easeOut" }}
              />
            </div>
            <div className="flex justify-between text-sm text-muted-foreground">
              <span className="font-medium">Step {currentStep + 1} of {STEPS.length}</span>
              <span className="text-gradient-electric font-semibold">{currentStepInfo.title}</span>
            </div>
          </motion.div>
        </div>

        {/* Step indicator with enhanced styling */}
        <motion.div 
          className="flex items-center justify-center mb-12"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.2 }}
        >
          {STEPS.map((step, index) => {
            const Icon = step.icon;
            const isActive = index === currentStep;
            const isComplete = index < currentStep;
            
            return (
              <React.Fragment key={step.id}>
                {index > 0 && (
                  <div className={cn(
                    'w-16 h-0.5 -mt-5 transition-all duration-500',
                    isComplete ? 'bg-gradient-to-r from-primary to-accent' : 'bg-muted/30'
                  )} />
                )}
                <motion.div 
                  className="flex flex-col items-center"
                  whileHover={{ scale: 1.05 }}
                  transition={{ type: "spring", stiffness: 400 }}
                >
                  <div className={cn(
                    'w-12 h-12 rounded-full flex items-center justify-center transition-all duration-500 relative',
                    isActive && 'bg-gradient-to-br from-primary to-accent text-white shadow-lg shadow-primary/25',
                    isComplete && !isActive && 'bg-primary/20 text-primary border-2 border-primary/50',
                    !isActive && !isComplete && 'bg-muted/30 text-muted-foreground border-2 border-muted/50'
                  )}>
                    {isActive && (
                      <div className="absolute inset-0 rounded-full bg-gradient-to-br from-primary to-accent animate-pulse opacity-50" />
                    )}
                    {isComplete && !isActive ? (
                      <CheckCircle className="h-6 w-6 relative z-10" />
                    ) : (
                      <Icon className="h-6 w-6 relative z-10" />
                    )}
                  </div>
                  <span className={cn(
                    'text-xs mt-3 hidden sm:block font-medium transition-all duration-300',
                    isActive ? 'text-foreground scale-110' : 'text-muted-foreground'
                  )}>
                    {step.title}
                  </span>
                </motion.div>
              </React.Fragment>
            );
          })}
        </motion.div>

        {/* Main content with glass morphism effect */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
        >
          <Card className="border-2 border-border/50 bg-card/80 backdrop-blur-xl relative overflow-hidden">
            {/* Card gradient overlay */}
            <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-accent/5 pointer-events-none" />
            
            <CardHeader className="relative">
              <div className="flex items-center gap-4">
                <div className="p-3 rounded-xl bg-gradient-to-br from-primary/10 to-accent/10 backdrop-blur-sm">
                  {React.createElement(currentStepInfo.icon, { className: 'h-7 w-7 text-primary' })}
                </div>
                <div>
                  <CardTitle className="text-2xl">{currentStepInfo.title}</CardTitle>
                  <CardDescription className="text-base mt-1">{currentStepInfo.description}</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="relative">
              <AnimatePresence mode="wait">
                <motion.div
                  key={currentStep}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ duration: 0.3 }}
                >
                  {renderStep()}
                </motion.div>
              </AnimatePresence>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  );
}