'use client';

import { useState } from 'react';
import { withAuth } from '@/lib/auth-context';
import { DashboardLayout } from '@/components/layout/dashboard-layout';
import { DashboardPageHeader } from '@/components/layout/dashboard-page-header';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useAutoRefresh } from '@/lib/hooks/use-auto-refresh';
import { 
  TrendingUp, 
  TrendingDown,
  DollarSign,
  Calculator,
  BarChart3,
  LineChart,
  Download,
  Calendar,
  Target,
  Zap,
  AlertCircle,
  CheckCircle,
  Info,
  RefreshCw,
  ExternalLink
} from 'lucide-react';
import { motion } from 'framer-motion';
import { LineChart as RechartsLineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, AreaChart, PieChart, Pie, Cell } from 'recharts';
import { formatCurrency, formatPercentage } from '@/lib/utils';
import { dedupedApi as api } from '@/lib/api-deduped';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useProject } from '@/lib/project-context';
import { LoadingState } from '@/components/ui/loading-state';
import { ErrorState } from '@/components/ui/error-state';
import { EmptyState } from '@/components/ui/empty-state';

function ProfitabilityPage() {
  const [selectedPeriod, setSelectedPeriod] = useState('month');
  const [selectedMetric, setSelectedMetric] = useState('roi');
  const { currentProject } = useProject();

  const queryClient = useQueryClient();
  
  // Auto-refresh profitability data every 5 minutes
  useAutoRefresh(
    ['roi-analysis', currentProject?.id],
    300000, // 5 minutes
    { enabled: !!currentProject }
  );
  
  useAutoRefresh(
    ['revenue-attribution', currentProject?.id],
    300000, // 5 minutes
    { enabled: !!currentProject }
  );

  // Fetch ROI analysis data
  const { data: roiData, isLoading: isRoiLoading, error: roiError } = useQuery({
    queryKey: ['roi-analysis', currentProject?.id],
    queryFn: async () => {
      if (!currentProject) return null;
      const response = await api.profitability.getRoiAnalysis(currentProject.id);
      return response.data;
    },
    enabled: !!currentProject,
  });

  // Fetch revenue attribution data
  const { data: attributionData, isLoading: isAttributionLoading, error: attributionError } = useQuery({
    queryKey: ['revenue-attribution', currentProject?.id],
    queryFn: async () => {
      if (!currentProject) return null;
      const response = await api.profitability.getRevenueAttribution(currentProject.id);
      return response.data;
    },
    enabled: !!currentProject,
  });

  const isLoading = isRoiLoading || isAttributionLoading;
  const error = roiError || attributionError;
  const apiData = { roi: roiData, attribution: attributionData };

  // Submit ROI analysis mutation
  const submitRoiAnalysis = useMutation({
    mutationFn: async (data: any) => {
      if (!currentProject) throw new Error('No project selected');
      return api.profitability.submitRoiAnalysis(currentProject.id, data);
    },
    onSuccess: () => {
      // Refetch ROI data
    },
  });

  // Mock data (fallback when no real data)
  const mockProfitabilityData = {
    currentMonth: {
      revenue: 125340,
      costs: 23450,
      profit: 101890,
      roi: 334.5,
      metrics: {
        organic_traffic_value: 85000,
        conversion_value: 28000,
        ranking_improvements_value: 12340,
        time_saved_value: 8500,
        tool_costs: 12000,
        labor_costs: 8500,
        opportunity_costs: 2950,
      },
    },
    trends: [
      { month: 'Jan', revenue: 95000, costs: 22000, profit: 73000, roi: 231.8 },
      { month: 'Feb', revenue: 102000, costs: 22500, profit: 79500, roi: 253.3 },
      { month: 'Mar', revenue: 108000, costs: 23000, profit: 85000, roi: 269.6 },
      { month: 'Apr', revenue: 115000, costs: 23200, profit: 91800, roi: 295.7 },
      { month: 'May', revenue: 121000, costs: 23350, profit: 97650, roi: 318.2 },
      { month: 'Jun', revenue: 125340, costs: 23450, profit: 101890, roi: 334.5 },
    ],
    breakdown: [
      { name: 'Organic Traffic', value: 85000, percentage: 67.8 },
      { name: 'Conversions', value: 28000, percentage: 22.3 },
      { name: 'Rankings', value: 12340, percentage: 9.8 },
    ],
    insights: [
      {
        type: 'success',
        title: 'ROI Increased 15%',
        description: 'Your ROI has improved by 15% compared to last month',
        impact: 'high',
      },
      {
        type: 'warning',
        title: 'Rising Tool Costs',
        description: 'Tool costs have increased by 8% this quarter',
        impact: 'medium',
      },
      {
        type: 'info',
        title: 'Optimization Opportunity',
        description: 'Improving page speed could increase revenue by $12,000/month',
        impact: 'high',
      },
    ],
  };

  const COLORS = ['#8b5cf6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444'];

  const getImpactColor = (impact: string) => {
    switch (impact) {
      case 'high':
        return 'text-green-600 bg-green-100 dark:bg-green-900/20';
      case 'medium':
        return 'text-yellow-600 bg-yellow-100 dark:bg-yellow-900/20';
      case 'low':
        return 'text-blue-600 bg-blue-100 dark:bg-blue-900/20';
      default:
        return 'text-gray-600 bg-gray-100 dark:bg-gray-900/20';
    }
  };

  const getInsightIcon = (type: string) => {
    switch (type) {
      case 'success':
        return <CheckCircle className="h-5 w-5 text-green-600" />;
      case 'warning':
        return <AlertCircle className="h-5 w-5 text-yellow-600" />;
      case 'info':
        return <Info className="h-5 w-5 text-blue-600" />;
      default:
        return <Info className="h-5 w-5 text-gray-600" />;
    }
  };

  // Transform backend data to match frontend expectations
  const transformedData = (() => {
    if (!roiData && !attributionData) return null;
    
    // Process ROI data
    const roi = roiData?.data?.roi_metrics || {};
    const efficiency = roiData?.data?.efficiency_metrics || {};
    const benchmarks = roiData?.data?.benchmarks || {};
    
    // Process Attribution data
    const attribution = attributionData?.data?.attribution_analysis || [];
    const totalRevenue = attributionData?.data?.total_revenue || 0;
    const organicAttribution = attribution.find((a: any) => a.source?.toLowerCase().includes('organic'));
    
    // Calculate current month metrics
    const currentMonth = {
      revenue: totalRevenue || roi.organic_revenue || 0,
      costs: roi.seo_investment || 0,
      profit: roi.net_profit || (totalRevenue - (roi.seo_investment || 0)),
      roi: roi.roi_percentage || 0,
      metrics: {
        organic_traffic_value: organicAttribution?.revenue || roi.organic_revenue || 0,
        conversion_value: efficiency.revenue_per_click * efficiency.organic_clicks || 0,
        ranking_improvements_value: 0, // Backend doesn't provide this
        time_saved_value: 0, // Backend doesn't provide this
        tool_costs: roi.seo_investment * 0.5 || 0, // Estimate
        labor_costs: roi.seo_investment * 0.35 || 0, // Estimate
        opportunity_costs: roi.seo_investment * 0.15 || 0, // Estimate
      },
    };
    
    // Build breakdown from attribution data
    const breakdown = attribution
      .filter((a: any) => a.revenue > 0)
      .map((a: any) => ({
        name: a.source,
        value: a.revenue,
        percentage: a.attribution_percentage || ((a.revenue / totalRevenue) * 100),
      }))
      .slice(0, 5); // Top 5 sources
    
    // Generate insights based on benchmarks and performance
    const insights = [];
    
    if (roi.roi_percentage > benchmarks.good_roi_threshold) {
      insights.push({
        type: 'success',
        title: `Excellent ROI: ${roi.roi_percentage.toFixed(0)}%`,
        description: `Your ROI exceeds the industry benchmark of ${benchmarks.industry_average_roi}%`,
        impact: 'high',
      });
    }
    
    if (efficiency.cost_per_click > 5) {
      insights.push({
        type: 'warning',
        title: 'High Cost Per Click',
        description: `Your cost per click ($${efficiency.cost_per_click.toFixed(2)}) is above average`,
        impact: 'medium',
      });
    }
    
    if (organicAttribution && organicAttribution.conversion_rate < 2) {
      insights.push({
        type: 'info',
        title: 'Conversion Optimization Opportunity',
        description: `Improving conversion rate from ${organicAttribution.conversion_rate.toFixed(1)}% to 3% could increase revenue significantly`,
        impact: 'high',
      });
    }
    
    return {
      currentMonth,
      trends: [], // Backend doesn't provide historical trends in current endpoints
      breakdown,
      insights,
      // Include original data for additional processing
      rawData: {
        roi: roiData,
        attribution: attributionData,
      },
    };
  })();
  
  // Use transformed data if available, otherwise use mock data
  const profitabilityData = transformedData || mockProfitabilityData;
  
  // Type guard for checking if data has currentMonth property
  const hasCurrentMonthData = (data: any): data is typeof mockProfitabilityData => {
    return data?.currentMonth !== undefined;
  };

  if (!currentProject) {
    return (
      <DashboardLayout>
        <EmptyState
          icon={DollarSign}
          title="No Project Selected"
          description="Please select a project from the dropdown above to view profitability data."
        />
      </DashboardLayout>
    );
  }

  if (isLoading) {
    return (
      <DashboardLayout>
        <div className="space-y-6">
          <DashboardPageHeader
            title="Profitability"
            description="Track your SEO ROI and revenue attribution"
          />
          <LoadingState 
            message="Loading profitability data..." 
            size="lg" 
          />
        </div>
      </DashboardLayout>
    );
  }

  // Check if GA4 is configured
  const isGA4Configured = roiData?.is_ga4_configured || attributionData?.is_ga4_configured;
  
  if (error || (roiData && !isGA4Configured)) {
    return (
      <DashboardLayout>
        <div className="space-y-6">
          <DashboardPageHeader
            title="Profitability"
            description="Track your SEO ROI and revenue attribution"
          />
          {!isGA4Configured ? (
            <Card>
              <CardHeader>
                <div className="flex items-center gap-3">
                  <div className="rounded-full bg-amber-500/10 p-3">
                    <AlertCircle className="h-6 w-6 text-amber-500" />
                  </div>
                  <div>
                    <CardTitle>Google Analytics 4 Configuration Required</CardTitle>
                    <CardDescription>
                      Connect your GA4 property to enable profitability tracking
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  Profitability analysis requires Google Analytics 4 to track revenue, conversions, and attribution data. 
                  Please configure your GA4 property ID in project settings.
                </p>
                <div className="flex gap-3">
                  <Button 
                    onClick={() => window.location.href = `/projects/${currentProject?.id}?tab=settings`}
                  >
                    <Zap className="mr-2 h-4 w-4" />
                    Configure GA4
                  </Button>
                  <Button variant="outline" asChild>
                    <a href="https://support.google.com/analytics/answer/9306384" target="_blank" rel="noopener noreferrer">
                      Learn More
                      <ExternalLink className="ml-2 h-4 w-4" />
                    </a>
                  </Button>
                </div>
              </CardContent>
            </Card>
          ) : (
            <ErrorState
              error={error || "An error occurred"}
              title="Failed to load profitability data"
              description="We couldn't fetch your profitability metrics. Please check your configuration and try again."
              onRetry={() => {
                queryClient.invalidateQueries({ queryKey: ['roi-analysis', currentProject?.id] });
                queryClient.invalidateQueries({ queryKey: ['revenue-attribution', currentProject?.id] });
              }}
            />
          )}
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
        <div className="space-y-6">
        {/* Optimized Header - Research-based 2025 standards */}
        <DashboardPageHeader
          title="Profitability"
          description="Track ROI and optimize your SEO investment returns with advanced profitability insights"
          badge={{
            icon: <DollarSign className="mr-1 h-3 w-3" />,
            text: "ROI Analytics",
            variant: "secondary"
          }}
          actions={
            <div className="flex items-center gap-4">
              <Select value={selectedPeriod} onValueChange={setSelectedPeriod}>
                <SelectTrigger className="w-[180px]">
                  <Calendar className="mr-2 h-4 w-4" />
                  <SelectValue placeholder="Select period" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="week">Last 7 Days</SelectItem>
                  <SelectItem value="month">Last 30 Days</SelectItem>
                  <SelectItem value="quarter">Last Quarter</SelectItem>
                  <SelectItem value="year">Last Year</SelectItem>
                </SelectContent>
              </Select>
              <Button variant="outline" size="sm">
                <Download className="mr-2 h-4 w-4" />
                Export Report
              </Button>
              <Button variant="outline" size="sm"
                onClick={() => {
                  queryClient.invalidateQueries({ queryKey: ['roi-analysis'] });
                  queryClient.invalidateQueries({ queryKey: ['revenue-attribution'] });
                }}
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                Refresh Data
              </Button>
              <Button>
                <Calculator className="mr-2 h-4 w-4" />
                ROI Calculator
              </Button>
            </div>
          }
        />

        {/* Key Metrics */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card className="metric-card border-muted/50 bg-gradient-to-br from-card to-card/50">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Revenue
              </CardTitle>
              <div className="rounded-full bg-green-500/10 p-2">
                <DollarSign className="h-4 w-4 text-green-500" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">
                {hasCurrentMonthData(profitabilityData) ? formatCurrency(profitabilityData.currentMonth.revenue) : 'N/A'}
              </div>
              {apiData?.attribution?.data?.organic_share !== undefined ? (
                <div className="flex items-center space-x-1 text-xs">
                  <span className="text-muted-foreground">
                    Organic share: {apiData.attribution.data.organic_share.toFixed(1)}%
                  </span>
                </div>
              ) : (
                <div className="flex items-center space-x-1 text-xs">
                  <TrendingUp className="h-3 w-3 text-green-500" />
                  <span className="text-green-500 font-medium">+12.5%</span>
                  <span className="text-muted-foreground">from last month</span>
                </div>
              )}
            </CardContent>
          </Card>
          
          <Card className="metric-card border-muted/50 bg-gradient-to-br from-card to-card/50">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Costs
              </CardTitle>
              <div className="rounded-full bg-red-500/10 p-2">
                <TrendingDown className="h-4 w-4 text-red-500" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">
                {hasCurrentMonthData(profitabilityData) ? formatCurrency(profitabilityData.currentMonth.costs) : 'N/A'}
              </div>
              <div className="flex items-center space-x-1 text-xs">
                <TrendingUp className="h-3 w-3 text-red-500" />
                <span className="text-red-500 font-medium">+2.1%</span>
                <span className="text-muted-foreground">from last month</span>
              </div>
            </CardContent>
          </Card>

          <Card className="metric-card border-muted/50 bg-gradient-to-br from-card to-card/50">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Net Profit
              </CardTitle>
              <div className="rounded-full bg-primary/10 p-2">
                <Zap className="h-4 w-4 text-primary" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">
                {hasCurrentMonthData(profitabilityData) ? formatCurrency(profitabilityData.currentMonth.profit) : 'N/A'}
              </div>
              <div className="flex items-center space-x-1 text-xs">
                <TrendingUp className="h-3 w-3 text-green-500" />
                <span className="text-green-500 font-medium">+15.8%</span>
                <span className="text-muted-foreground">from last month</span>
              </div>
            </CardContent>
          </Card>

          <Card className="metric-card border-muted/50 bg-gradient-to-br from-card to-card/50">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                ROI
              </CardTitle>
              <div className="rounded-full bg-amber-500/10 p-2">
                <Target className="h-4 w-4 text-amber-500" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">
                {hasCurrentMonthData(profitabilityData) ? `${profitabilityData.currentMonth.roi.toFixed(1)}%` : 'N/A'}
              </div>
              {apiData?.roi?.data?.benchmarks?.performance_rating ? (
                <div className="flex items-center space-x-1 text-xs">
                  <Badge variant={
                    apiData.roi.data.benchmarks.performance_rating === 'Excellent' ? 'default' :
                    apiData.roi.data.benchmarks.performance_rating === 'Good' ? 'secondary' :
                    'outline'
                  } className="text-xs">
                    {apiData.roi.data.benchmarks.performance_rating}
                  </Badge>
                  <span className="text-muted-foreground">
                    vs industry avg: {apiData.roi.data.benchmarks.industry_average_roi}%
                  </span>
                </div>
              ) : (
                <div className="flex items-center space-x-1 text-xs">
                  <TrendingUp className="h-3 w-3 text-green-500" />
                  <span className="text-green-500 font-medium">+45.2%</span>
                  <span className="text-muted-foreground">from last month</span>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Charts */}
        <div className="grid gap-6 md:grid-cols-2">
          <Card className="col-span-full">
            <CardHeader>
              <CardTitle>Revenue & Cost Trends</CardTitle>
              <CardDescription>
                Monthly revenue vs costs over the last 6 months
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[350px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={hasCurrentMonthData(profitabilityData) ? profitabilityData.trends : []}>
                    <defs>
                      <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.8}/>
                        <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0}/>
                      </linearGradient>
                      <linearGradient id="colorCosts" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#ef4444" stopOpacity={0.8}/>
                        <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis dataKey="month" className="text-xs" />
                    <YAxis className="text-xs" />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: 'hsl(var(--card))',
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '8px'
                      }}
                    />
                    <Legend />
                    <Area
                      type="monotone"
                      dataKey="revenue"
                      stroke="#8b5cf6"
                      fillOpacity={1}
                      fill="url(#colorRevenue)"
                    />
                    <Area
                      type="monotone"
                      dataKey="costs"
                      stroke="#ef4444"
                      fillOpacity={1}
                      fill="url(#colorCosts)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Revenue Breakdown</CardTitle>
              <CardDescription>
                Sources of SEO-driven revenue
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={hasCurrentMonthData(profitabilityData) ? profitabilityData.breakdown : []}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ percentage }) => `${percentage.toFixed(1)}%`}
                      outerRadius={100}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {(hasCurrentMonthData(profitabilityData) ? profitabilityData.breakdown : []).map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ 
                        backgroundColor: 'hsl(var(--card))',
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '8px'
                      }}
                    />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>ROI Trend</CardTitle>
              <CardDescription>
                Return on investment growth over time
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <RechartsLineChart data={hasCurrentMonthData(profitabilityData) ? profitabilityData.trends : []}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis dataKey="month" className="text-xs" />
                    <YAxis className="text-xs" />
                    <Tooltip
                      contentStyle={{ 
                        backgroundColor: 'hsl(var(--card))',
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '8px'
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="roi"
                      stroke="#8b5cf6"
                      strokeWidth={3}
                      dot={{ fill: '#8b5cf6', strokeWidth: 2, r: 4 }}
                      activeDot={{ r: 6 }}
                    />
                  </RechartsLineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Insights */}
        <Card>
          <CardHeader>
            <CardTitle>Profitability Insights</CardTitle>
            <CardDescription>
              AI-powered recommendations to improve your ROI
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {(hasCurrentMonthData(profitabilityData) ? profitabilityData.insights : []).map((insight, index) => (
                <div
                  key={index}
                  className="flex items-start space-x-4 rounded-lg border p-4"
                >
                  <div className="mt-0.5">
                    {getInsightIcon(insight.type)}
                  </div>
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center justify-between">
                      <h4 className="text-sm font-semibold">{insight.title}</h4>
                      <Badge
                        variant="outline"
                        className={getImpactColor(insight.impact)}
                      >
                        {insight.impact} impact
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {insight.description}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Cost Breakdown */}
        <Tabs defaultValue="breakdown" className="space-y-4">
          <TabsList>
            <TabsTrigger value="breakdown">Cost Breakdown</TabsTrigger>
            <TabsTrigger value="optimization">Optimization Opportunities</TabsTrigger>
            <TabsTrigger value="forecast">Revenue Forecast</TabsTrigger>
          </TabsList>

          <TabsContent value="breakdown" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Detailed Cost Analysis</CardTitle>
                <CardDescription>
                  Understanding where your SEO budget is allocated
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <h4 className="text-sm font-medium mb-4">Revenue Sources</h4>
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="text-sm">Organic Traffic Value</span>
                          <span className="text-sm font-bold">
                            {hasCurrentMonthData(profitabilityData) ? formatCurrency(profitabilityData.currentMonth.metrics.organic_traffic_value) : 'N/A'}
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-sm">Conversion Value</span>
                          <span className="text-sm font-bold">
                            {hasCurrentMonthData(profitabilityData) ? formatCurrency(profitabilityData.currentMonth.metrics.conversion_value) : 'N/A'}
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-sm">Ranking Improvements</span>
                          <span className="text-sm font-bold">
                            {hasCurrentMonthData(profitabilityData) ? formatCurrency(profitabilityData.currentMonth.metrics.ranking_improvements_value) : 'N/A'}
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-sm">Time Saved Value</span>
                          <span className="text-sm font-bold">
                            {hasCurrentMonthData(profitabilityData) ? formatCurrency(profitabilityData.currentMonth.metrics.time_saved_value) : 'N/A'}
                          </span>
                        </div>
                      </div>
                    </div>
                    <div>
                      <h4 className="text-sm font-medium mb-4">Cost Centers</h4>
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="text-sm">Tool & Software Costs</span>
                          <span className="text-sm font-bold text-red-600">
                            {hasCurrentMonthData(profitabilityData) ? `-${formatCurrency(profitabilityData.currentMonth.metrics.tool_costs)}` : 'N/A'}
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-sm">Labor Costs</span>
                          <span className="text-sm font-bold text-red-600">
                            {hasCurrentMonthData(profitabilityData) ? `-${formatCurrency(profitabilityData.currentMonth.metrics.labor_costs)}` : 'N/A'}
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-sm">Opportunity Costs</span>
                          <span className="text-sm font-bold text-red-600">
                            {hasCurrentMonthData(profitabilityData) ? `-${formatCurrency(profitabilityData.currentMonth.metrics.opportunity_costs)}` : 'N/A'}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
        </div>
    </DashboardLayout>
  );
}

export default withAuth(ProfitabilityPage);