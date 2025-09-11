'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { CreditCard, Download, Receipt, Clock, CheckCircle, XCircle, Crown, Sparkles, Zap, Calendar, DollarSign, TrendingUp } from 'lucide-react';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { api } from '@/lib/api-client';
import { useAuth } from '@/lib/auth-context';
import { useProject } from '@/lib/project-context';
import { useToast } from '@/components/ui/use-toast';
import { formatDistanceToNow, format } from 'date-fns';
import { cn } from '@/lib/utils';
import { motion, useScroll, useTransform } from 'framer-motion';
import { SEOOrb } from '@/components/ui/seo-orb';
import { LoadingState } from '@/components/ui/loading-state';
import { ErrorState } from '@/components/ui/error-state';

interface SubscriptionPlan {
  id: string;
  name: string;
  description: string;
  price: number;
  billing_period: 'monthly' | 'yearly';
  features: string[];
  limits: {
    sites: number;
    crawls_per_month: number;
    team_members: number;
    api_calls: number;
  };
  is_popular?: boolean;
  is_current?: boolean;
}

interface Subscription {
  id: string;
  plan: SubscriptionPlan;
  status: 'active' | 'canceled' | 'past_due' | 'trialing';
  current_period_start: string;
  current_period_end: string;
  cancel_at_period_end: boolean;
  trial_end?: string;
}

interface UsageMetrics {
  sites_used: number;
  sites_limit: number;
  crawls_used: number;
  crawls_limit: number;
  team_members_used: number;
  team_members_limit: number;
  api_calls_used: number;
  api_calls_limit: number;
}

interface Invoice {
  id: string;
  amount: number;
  currency: string;
  status: 'paid' | 'pending' | 'failed';
  created_at: string;
  due_date: string;
  pdf_url?: string;
  description: string;
}

export default function BillingPage() {
  const router = useRouter();
  const { user } = useAuth();
  const { currentOrganization: organization } = useProject();
  const { toast } = useToast();
  
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [usage, setUsage] = useState<UsageMetrics | null>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // Parallax and scroll effects
  const { scrollY } = useScroll();
  const heroY = useTransform(scrollY, [0, 500], [0, 150]);
  const orbScale = useTransform(scrollY, [0, 500], [1, 0.8]);

  useEffect(() => {
    fetchBillingData();
  }, [organization]);

  const fetchBillingData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // For now, we'll create mock data since the API endpoints might not be fully implemented
      const mockSubscription: Subscription = {
        id: 'sub_123',
        plan: {
          id: 'plan_pro',
          name: 'Professional',
          description: 'Perfect for growing businesses',
          price: 49,
          billing_period: 'monthly',
          features: [
            'Up to 10 sites',
            '1,000 crawls per month',
            '10 team members',
            '50,000 API calls',
            'Advanced analytics',
            'Priority support'
          ],
          limits: {
            sites: 10,
            crawls_per_month: 1000,
            team_members: 10,
            api_calls: 50000
          },
          is_current: true
        },
        status: 'active',
        current_period_start: new Date(Date.now() - 15 * 24 * 60 * 60 * 1000).toISOString(),
        current_period_end: new Date(Date.now() + 15 * 24 * 60 * 60 * 1000).toISOString(),
        cancel_at_period_end: false
      };

      const mockPlans: SubscriptionPlan[] = [
        {
          id: 'plan_starter',
          name: 'Starter',
          description: 'Perfect for small projects',
          price: 19,
          billing_period: 'monthly',
          features: [
            'Up to 3 sites',
            '100 crawls per month',
            '3 team members',
            '10,000 API calls',
            'Basic analytics',
            'Email support'
          ],
          limits: {
            sites: 3,
            crawls_per_month: 100,
            team_members: 3,
            api_calls: 10000
          }
        },
        {
          id: 'plan_pro',
          name: 'Professional',
          description: 'Perfect for growing businesses',
          price: 49,
          billing_period: 'monthly',
          features: [
            'Up to 10 sites',
            '1,000 crawls per month',
            '10 team members',
            '50,000 API calls',
            'Advanced analytics',
            'Priority support'
          ],
          limits: {
            sites: 10,
            crawls_per_month: 1000,
            team_members: 10,
            api_calls: 50000
          },
          is_popular: true,
          is_current: true
        },
        {
          id: 'plan_enterprise',
          name: 'Enterprise',
          description: 'For large organizations',
          price: 149,
          billing_period: 'monthly',
          features: [
            'Unlimited sites',
            '10,000 crawls per month',
            'Unlimited team members',
            '500,000 API calls',
            'Custom analytics',
            '24/7 phone support',
            'Custom integrations'
          ],
          limits: {
            sites: -1, // Unlimited
            crawls_per_month: 10000,
            team_members: -1,
            api_calls: 500000
          }
        }
      ];

      const mockUsage: UsageMetrics = {
        sites_used: 2,
        sites_limit: 10,
        crawls_used: 342,
        crawls_limit: 1000,
        team_members_used: 4,
        team_members_limit: 10,
        api_calls_used: 12456,
        api_calls_limit: 50000
      };

      const mockInvoices: Invoice[] = [
        {
          id: 'inv_001',
          amount: 49.00,
          currency: 'USD',
          status: 'paid',
          created_at: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
          due_date: new Date(Date.now() - 25 * 24 * 60 * 60 * 1000).toISOString(),
          description: 'Professional Plan - Monthly'
        },
        {
          id: 'inv_002',
          amount: 49.00,
          currency: 'USD',
          status: 'paid',
          created_at: new Date(Date.now() - 60 * 24 * 60 * 60 * 1000).toISOString(),
          due_date: new Date(Date.now() - 55 * 24 * 60 * 60 * 1000).toISOString(),
          description: 'Professional Plan - Monthly'
        }
      ];

      // Try to fetch real data, fall back to mock if not available
      try {
        const [subscriptionResponse, plansResponse, usageResponse] = await Promise.all([
          api.subscriptions.getCurrent().catch(() => ({ data: mockSubscription })),
          api.subscriptions.getPlans().catch(() => ({ data: mockPlans })),
          api.subscriptions.getUsage().catch(() => ({ data: mockUsage }))
        ]);

        setSubscription(subscriptionResponse.data);
        setPlans(plansResponse.data);
        setUsage(usageResponse.data);
        setInvoices(mockInvoices); // Use mock invoices for now
      } catch (apiError) {
        // If API fails, use mock data
        setSubscription(mockSubscription);
        setPlans(mockPlans);
        setUsage(mockUsage);
        setInvoices(mockInvoices);
      }
      
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch billing data'));
      console.error('Failed to fetch billing data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handlePlanChange = async (planId: string) => {
    try {
      setActionLoading(planId);
      await api.subscriptions.subscribe({ plan_id: planId });
      toast({
        title: 'Plan updated',
        description: 'Your subscription has been updated successfully.',
      });
      await fetchBillingData();
    } catch (err) {
      toast({
        title: 'Error',
        description: 'Failed to update subscription. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setActionLoading(null);
    }
  };

  const handleCancelSubscription = async () => {
    try {
      setActionLoading('cancel');
      await api.subscriptions.performAction({ action: 'cancel' });
      toast({
        title: 'Subscription canceled',
        description: 'Your subscription will remain active until the end of the billing period.',
      });
      await fetchBillingData();
    } catch (err) {
      toast({
        title: 'Error',
        description: 'Failed to cancel subscription. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setActionLoading(null);
    }
  };

  const formatCurrency = (amount: number, currency = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency
    }).format(amount);
  };

  const getUsagePercentage = (used: number, limit: number) => {
    if (limit === -1) return 0; // Unlimited
    return Math.min((used / limit) * 100, 100);
  };

  const getUsageColor = (percentage: number) => {
    if (percentage >= 90) return 'text-red-500';
    if (percentage >= 70) return 'text-yellow-500';
    return 'text-green-500';
  };

  if (!organization) {
    return (
      <div className="min-h-screen bg-background text-foreground relative noise-overlay">
        <DashboardLayout>
          <div className="container mx-auto p-6">
            <Card>
              <CardContent className="text-center py-8">
                <h3 className="text-lg font-semibold mb-2">No Organization Selected</h3>
                <p className="text-muted-foreground mb-4">
                  Please select an organization to manage billing
                </p>
                <Button onClick={() => router.push("/organizations")}>
                  Go to Organizations
                </Button>
              </CardContent>
            </Card>
          </div>
        </DashboardLayout>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-background text-foreground relative noise-overlay">
        <DashboardLayout>
          <LoadingState message="Loading billing information..." size="lg" />
        </DashboardLayout>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background text-foreground relative noise-overlay">
        <DashboardLayout>
          <ErrorState
            error={error}
            title="Failed to load billing"
            description="We couldn't fetch your billing information. Please try again."
            onRetry={fetchBillingData}
          />
        </DashboardLayout>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-foreground relative noise-overlay">
      {/* Background gradient mesh */}
      <div className="fixed inset-0 gradient-mesh opacity-20 dark:opacity-10" />
      
      {/* Enhanced floating 3D orb */}
      <motion.div
        className="fixed right-[-300px] top-1/4 w-[600px] h-[600px] lg:w-[800px] lg:h-[800px] pointer-events-none"
        style={{ y: heroY, scale: orbScale }}
      >
        <SEOOrb className="scale-100 opacity-30" />
      </motion.div>
      
      {/* Animated background elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
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
      </div>

      <DashboardLayout>
        <div className="space-y-8 relative z-10">
          {/* Enhanced Header */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="flex items-center justify-between"
          >
            <div>
              <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: 0.1 }}
              >
                <Badge variant="secondary" className="mb-4 animate-slide-up-fade">
                  <Sparkles className="mr-1 h-3 w-3" />
                  Subscription Management
                </Badge>
              </motion.div>
              
              <motion.h1 
                className="text-5xl sm:text-6xl font-bold tracking-tighter mb-4 leading-[0.9]"
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: 0.2 }}
              >
                <span className="block">Billing &</span>
                <span className="block text-gradient-electric">Subscriptions</span>
              </motion.h1>
              
              <motion.p 
                className="text-lg sm:text-xl text-muted-foreground leading-relaxed max-w-2xl"
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: 0.3 }}
              >
                Manage your subscription, usage, and billing information
              </motion.p>
            </div>
          </motion.div>

          <div className="grid gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2 space-y-6">
              {/* Current Subscription */}
              {subscription && (
                <Card className="border-primary/20 bg-gradient-to-br from-primary/[0.02] via-accent/[0.02] to-transparent">
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div>
                        <CardTitle className="flex items-center gap-2">
                          <Crown className="h-5 w-5 text-primary" />
                          Current Subscription
                        </CardTitle>
                        <CardDescription>
                          Your active plan and billing information
                        </CardDescription>
                      </div>
                      <Badge 
                        variant={subscription.status === 'active' ? 'default' : 'secondary'}
                        className="capitalize"
                      >
                        {subscription.status}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="text-2xl font-bold">{subscription.plan.name}</h3>
                        <p className="text-muted-foreground">{subscription.plan.description}</p>
                      </div>
                      <div className="text-right">
                        <div className="text-3xl font-bold">
                          {formatCurrency(subscription.plan.price)}
                        </div>
                        <div className="text-sm text-muted-foreground">
                          per {subscription.plan.billing_period === 'yearly' ? 'year' : 'month'}
                        </div>
                      </div>
                    </div>
                    
                    <Separator />
                    
                    <div className="grid gap-4 md:grid-cols-2">
                      <div>
                        <div className="text-sm text-muted-foreground">Billing Period</div>
                        <div className="font-medium">
                          {format(new Date(subscription.current_period_start), 'MMM dd, yyyy')} - {format(new Date(subscription.current_period_end), 'MMM dd, yyyy')}
                        </div>
                      </div>
                      <div>
                        <div className="text-sm text-muted-foreground">Next Payment</div>
                        <div className="font-medium">
                          {format(new Date(subscription.current_period_end), 'MMM dd, yyyy')}
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex gap-2">
                      <Button 
                        variant="outline" 
                        onClick={handleCancelSubscription}
                        disabled={subscription.cancel_at_period_end || actionLoading === 'cancel'}
                      >
                        {subscription.cancel_at_period_end ? 'Cancellation Pending' : actionLoading === 'cancel' ? 'Canceling...' : 'Cancel Subscription'}
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Usage Overview */}
              {usage && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <TrendingUp className="h-5 w-5" />
                      Usage Overview
                    </CardTitle>
                    <CardDescription>
                      Current usage across your plan limits
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    <div className="grid gap-4 md:grid-cols-2">
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium">Sites</span>
                          <span className="text-sm text-muted-foreground">
                            {usage.sites_used} / {usage.sites_limit === -1 ? '∞' : usage.sites_limit}
                          </span>
                        </div>
                        <Progress 
                          value={getUsagePercentage(usage.sites_used, usage.sites_limit)} 
                          className="h-2"
                        />
                      </div>
                      
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium">Team Members</span>
                          <span className="text-sm text-muted-foreground">
                            {usage.team_members_used} / {usage.team_members_limit === -1 ? '∞' : usage.team_members_limit}
                          </span>
                        </div>
                        <Progress 
                          value={getUsagePercentage(usage.team_members_used, usage.team_members_limit)} 
                          className="h-2"
                        />
                      </div>
                      
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium">Crawls (This Month)</span>
                          <span className={cn("text-sm", getUsageColor(getUsagePercentage(usage.crawls_used, usage.crawls_limit)))}>
                            {usage.crawls_used} / {usage.crawls_limit === -1 ? '∞' : usage.crawls_limit}
                          </span>
                        </div>
                        <Progress 
                          value={getUsagePercentage(usage.crawls_used, usage.crawls_limit)} 
                          className="h-2"
                        />
                      </div>
                      
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium">API Calls (This Month)</span>
                          <span className={cn("text-sm", getUsageColor(getUsagePercentage(usage.api_calls_used, usage.api_calls_limit)))}>
                            {usage.api_calls_used.toLocaleString()} / {usage.api_calls_limit === -1 ? '∞' : usage.api_calls_limit.toLocaleString()}
                          </span>
                        </div>
                        <Progress 
                          value={getUsagePercentage(usage.api_calls_used, usage.api_calls_limit)} 
                          className="h-2"
                        />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Invoices */}
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="flex items-center gap-2">
                        <Receipt className="h-5 w-5" />
                        Recent Invoices
                      </CardTitle>
                      <CardDescription>
                        Your billing history and downloadable receipts
                      </CardDescription>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {invoices.map((invoice) => (
                      <div key={invoice.id} className="flex items-center justify-between p-4 border rounded-lg">
                        <div className="flex items-center gap-3">
                          <div className="p-2 bg-muted rounded-full">
                            <Receipt className="h-4 w-4" />
                          </div>
                          <div>
                            <div className="font-medium">{invoice.description}</div>
                            <div className="text-sm text-muted-foreground">
                              {format(new Date(invoice.created_at), 'MMM dd, yyyy')}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <div className="text-right">
                            <div className="font-medium">{formatCurrency(invoice.amount)}</div>
                            <div className="flex items-center gap-1">
                              {invoice.status === 'paid' ? (
                                <CheckCircle className="h-3 w-3 text-green-500" />
                              ) : invoice.status === 'pending' ? (
                                <Clock className="h-3 w-3 text-yellow-500" />
                              ) : (
                                <XCircle className="h-3 w-3 text-red-500" />
                              )}
                              <span className={cn(
                                "text-xs capitalize",
                                invoice.status === 'paid' && "text-green-500",
                                invoice.status === 'pending' && "text-yellow-500",
                                invoice.status === 'failed' && "text-red-500"
                              )}>
                                {invoice.status}
                              </span>
                            </div>
                          </div>
                          <Button variant="outline" size="sm">
                            <Download className="h-3 w-3 mr-1" />
                            Download
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Available Plans */}
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Zap className="h-5 w-5" />
                    Available Plans
                  </CardTitle>
                  <CardDescription>
                    Upgrade or change your subscription plan
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {plans.map((plan) => (
                    <Card 
                      key={plan.id} 
                      className={cn(
                        "relative transition-all cursor-pointer hover:shadow-md",
                        plan.is_current && "ring-2 ring-primary",
                        plan.is_popular && "border-primary/50"
                      )}
                    >
                      {plan.is_popular && (
                        <div className="absolute -top-2 left-4">
                          <Badge variant="default" className="text-xs">
                            Most Popular
                          </Badge>
                        </div>
                      )}
                      {plan.is_current && (
                        <div className="absolute -top-2 right-4">
                          <Badge variant="secondary" className="text-xs">
                            Current Plan
                          </Badge>
                        </div>
                      )}
                      
                      <CardHeader className="pb-3">
                        <CardTitle className="text-lg">{plan.name}</CardTitle>
                        <CardDescription className="text-xs">{plan.description}</CardDescription>
                        <div className="flex items-baseline gap-1">
                          <span className="text-2xl font-bold">{formatCurrency(plan.price)}</span>
                          <span className="text-sm text-muted-foreground">
                            /{plan.billing_period === 'yearly' ? 'year' : 'month'}
                          </span>
                        </div>
                      </CardHeader>
                      
                      <CardContent className="space-y-3">
                        <ul className="space-y-1 text-xs">
                          {plan.features.slice(0, 4).map((feature, index) => (
                            <li key={index} className="flex items-center gap-2">
                              <CheckCircle className="h-3 w-3 text-green-500 flex-shrink-0" />
                              {feature}
                            </li>
                          ))}
                        </ul>
                        
                        {!plan.is_current && (
                          <Button 
                            className="w-full" 
                            variant={plan.is_popular ? "default" : "outline"}
                            onClick={() => handlePlanChange(plan.id)}
                            disabled={actionLoading === plan.id}
                          >
                            {actionLoading === plan.id ? 'Processing...' : subscription ? 'Switch Plan' : 'Choose Plan'}
                          </Button>
                        )}
                      </CardContent>
                    </Card>
                  ))}
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </DashboardLayout>
    </div>
  );
}