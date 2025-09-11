'use client';

import { useState, useEffect } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Area,
  AreaChart,
} from 'recharts';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Progress } from '@/components/ui/progress';
import { TrendingUp, TrendingDown, Minus, Activity, Zap, Clock, Layout, RefreshCw } from 'lucide-react';
import { formatDate } from '@/lib/utils';

interface PerformanceMetric {
  date: string;
  lcp: number;
  fid?: number;
  cls: number;
  inp?: number;
  ttfb?: number;
  fcp?: number;
  si?: number;
  performanceScore?: number;
}

interface PerformanceTrendsChartProps {
  data: PerformanceMetric[];
  isLoading?: boolean;
  period?: string;
  onPeriodChange?: (period: string) => void;
  isCollecting?: boolean;
  collectionProgress?: number;
  collectionStage?: string;
}

const metricInfo = {
  lcp: {
    name: 'Largest Contentful Paint',
    unit: 's',
    goodThreshold: 2.5,
    poorThreshold: 4.0,
    color: '#8b5cf6',
  },
  fid: {
    name: 'First Input Delay',
    unit: 'ms',
    goodThreshold: 100,
    poorThreshold: 300,
    color: '#06b6d4',
  },
  cls: {
    name: 'Cumulative Layout Shift',
    unit: '',
    goodThreshold: 0.1,
    poorThreshold: 0.25,
    color: '#f59e0b',
  },
  inp: {
    name: 'Interaction to Next Paint',
    unit: 'ms',
    goodThreshold: 200,
    poorThreshold: 500,
    color: '#10b981',
  },
  ttfb: {
    name: 'Time to First Byte',
    unit: 'ms',
    goodThreshold: 800,
    poorThreshold: 1800,
    color: '#ef4444',
  },
  fcp: {
    name: 'First Contentful Paint',
    unit: 's',
    goodThreshold: 1.8,
    poorThreshold: 3.0,
    color: '#3b82f6',
  },
  si: {
    name: 'Speed Index',
    unit: 's',
    goodThreshold: 3.4,
    poorThreshold: 5.8,
    color: '#ec4899',
  },
};

function getMetricStatus(value: number, metric: keyof typeof metricInfo) {
  const info = metricInfo[metric];
  if (value <= info.goodThreshold) return 'good';
  if (value <= info.poorThreshold) return 'needs-improvement';
  return 'poor';
}

function getStatusColor(status: string) {
  switch (status) {
    case 'good':
      return 'text-green-600';
    case 'needs-improvement':
      return 'text-yellow-600';
    case 'poor':
      return 'text-red-600';
    default:
      return 'text-gray-600';
  }
}

function getTrendIcon(current: number, previous: number, metric: keyof typeof metricInfo) {
  const percentChange = ((current - previous) / previous) * 100;
  const improved = current < previous; // Lower is better for all metrics
  
  if (Math.abs(percentChange) < 1) {
    return <Minus className="h-4 w-4 text-gray-500" />;
  }
  
  if (improved) {
    return <TrendingDown className="h-4 w-4 text-green-600" />;
  } else {
    return <TrendingUp className="h-4 w-4 text-red-600" />;
  }
}

export function PerformanceTrendsChart({
  data,
  isLoading,
  period = '30d',
  onPeriodChange,
  isCollecting = false,
  collectionProgress = 0,
  collectionStage = '',
}: PerformanceTrendsChartProps) {
  const [selectedMetric, setSelectedMetric] = useState<'all' | keyof typeof metricInfo>('all');

  if (isLoading || isCollecting) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                Performance Trends
                {isCollecting && (
                  <Badge variant="secondary" className="animate-pulse">
                    <Activity className="h-3 w-3 mr-1" />
                    Collecting
                  </Badge>
                )}
              </CardTitle>
              <CardDescription>
                {isCollecting 
                  ? collectionStage || 'Collecting performance data...'
                  : 'Loading performance trends data...'
                }
              </CardDescription>
            </div>
            {isCollecting && (
              <Badge variant="outline" className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {Math.round(collectionProgress)}%
              </Badge>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {isCollecting && (
            <div className="space-y-6">
              {/* Data Collection Progress */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="font-medium text-blue-800">{collectionStage || 'Collecting data...'}</span>
                  <span className="text-blue-700 font-bold">{Math.round(collectionProgress)}%</span>
                </div>
                <Progress value={collectionProgress} className="h-2 mb-3" />
                
                {/* Collection stages indicator */}
                <div className="grid grid-cols-4 gap-2 text-xs">
                  <div className={`text-center p-2 rounded ${collectionProgress >= 25 ? 'bg-green-100 text-green-700' : 'bg-gray-100'}`}>
                    Lab Data
                  </div>
                  <div className={`text-center p-2 rounded ${collectionProgress >= 50 ? 'bg-green-100 text-green-700' : 'bg-gray-100'}`}>
                    Field Data
                  </div>
                  <div className={`text-center p-2 rounded ${collectionProgress >= 75 ? 'bg-green-100 text-green-700' : 'bg-gray-100'}`}>
                    Processing
                  </div>
                  <div className={`text-center p-2 rounded ${collectionProgress >= 95 ? 'bg-green-100 text-green-700' : 'bg-gray-100'}`}>
                    Finalizing
                  </div>
                </div>
                
                {/* Current metric being collected */}
                {collectionStage && collectionStage.includes('metric') && (
                  <div className="mt-3 p-2 bg-white rounded border">
                    <p className="text-xs font-medium mb-1">Currently processing:</p>
                    <p className="text-xs text-muted-foreground">
                      {collectionStage}
                    </p>
                  </div>
                )}
              </div>
              
              {/* Placeholder skeleton for chart area during collection */}
              <Skeleton className="h-[400px] w-full" />
            </div>
          )}
          {!isCollecting && <Skeleton className="h-[400px] w-full" />}
        </CardContent>
      </Card>
    );
  }

  if (!data || data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Performance Trends</CardTitle>
          <CardDescription>No performance data available for the selected period</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-[400px] text-muted-foreground">
            <Activity className="h-8 w-8 mr-2" />
            <span>Start collecting data to see trends</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Calculate current and previous values for trend indicators
  const latestData = data[data.length - 1];
  const previousData = data[data.length - 2] || data[data.length - 1];

  // Format data for charts
  const formattedData = data.map(item => ({
    ...item,
    date: formatDate(item.date),
  }));

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Performance Trends</CardTitle>
            <CardDescription>
              Core Web Vitals trends over the selected period
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Select value={period} onValueChange={onPeriodChange}>
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="7d">Last 7 days</SelectItem>
                <SelectItem value="30d">Last 30 days</SelectItem>
                <SelectItem value="90d">Last 90 days</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="overview" className="space-y-4">
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="core-vitals">Core Web Vitals</TabsTrigger>
            <TabsTrigger value="performance">Performance Score</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-4">
            {/* Metric Summary Cards */}
            <div className="grid gap-4 md:grid-cols-3 mb-6">
              {(['lcp', 'cls', 'inp'] as const).map((metric) => {
                const current = latestData[metric];
                const previous = previousData[metric];
                if (current === undefined) return null;

                const status = getMetricStatus(current, metric);
                const info = metricInfo[metric];

                return (
                  <div key={metric} className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium">{info.name}</span>
                      {getTrendIcon(current, previous || current, metric)}
                    </div>
                    <div className={`text-2xl font-bold ${getStatusColor(status)}`}>
                      {current.toFixed(metric === 'cls' ? 3 : 1)}{info.unit}
                    </div>
                    <Badge
                      variant={
                        status === 'good'
                          ? 'default'
                          : status === 'needs-improvement'
                          ? 'secondary'
                          : 'destructive'
                      }
                      className="mt-1"
                    >
                      {status.replace('-', ' ')}
                    </Badge>
                  </div>
                );
              })}
            </div>

            {/* All Metrics Chart */}
            <div className="h-[400px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={formattedData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  {selectedMetric === 'all' ? (
                    <>
                      <Line
                        type="monotone"
                        dataKey="lcp"
                        stroke={metricInfo.lcp.color}
                        name="LCP (s)"
                        strokeWidth={2}
                      />
                      <Line
                        type="monotone"
                        dataKey="cls"
                        stroke={metricInfo.cls.color}
                        name="CLS"
                        strokeWidth={2}
                      />
                      {data[0].inp !== undefined && (
                        <Line
                          type="monotone"
                          dataKey="inp"
                          stroke={metricInfo.inp.color}
                          name="INP (ms)"
                          strokeWidth={2}
                        />
                      )}
                    </>
                  ) : (
                    <Line
                      type="monotone"
                      dataKey={selectedMetric}
                      stroke={metricInfo[selectedMetric].color}
                      name={`${metricInfo[selectedMetric].name} (${metricInfo[selectedMetric].unit})`}
                      strokeWidth={2}
                    />
                  )}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </TabsContent>

          <TabsContent value="core-vitals" className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              {(Object.keys(metricInfo) as Array<keyof typeof metricInfo>).map((metric) => {
                const metricData = formattedData.filter(d => d[metric] !== undefined);
                if (metricData.length === 0) return null;

                const info = metricInfo[metric];
                return (
                  <Card key={metric}>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-base">{info.name}</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="h-[200px]">
                        <ResponsiveContainer width="100%" height="100%">
                          <AreaChart data={metricData}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="date" />
                            <YAxis />
                            <Tooltip />
                            <Area
                              type="monotone"
                              dataKey={metric}
                              stroke={info.color}
                              fill={info.color}
                              fillOpacity={0.3}
                            />
                          </AreaChart>
                        </ResponsiveContainer>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </TabsContent>

          <TabsContent value="performance" className="space-y-4">
            {formattedData[0].performanceScore !== undefined ? (
              <div className="h-[400px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={formattedData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis domain={[0, 100]} />
                    <Tooltip />
                    <Legend />
                    <Area
                      type="monotone"
                      dataKey="performanceScore"
                      stroke="#8b5cf6"
                      fill="#8b5cf6"
                      fillOpacity={0.3}
                      name="Performance Score"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="flex items-center justify-center h-[400px] text-muted-foreground">
                <Zap className="h-8 w-8 mr-2" />
                <span>Performance score data not available</span>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}