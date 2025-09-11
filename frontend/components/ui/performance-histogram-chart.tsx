'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts';
import { Activity, Users, Smartphone, Monitor, Tablet, TrendingUp, TrendingDown, AlertCircle } from 'lucide-react';

interface HistogramData {
  good: number;
  needs_improvement: number;
  poor: number;
}

interface PerformanceHistogramChartProps {
  data: {
    mobile_field_performance_metrics?: {
      histogram?: {
        lcp?: HistogramData;
        fid?: HistogramData;
        cls?: HistogramData;
        inp?: HistogramData;
      };
    };
    desktop_field_performance_metrics?: {
      histogram?: {
        lcp?: HistogramData;
        fid?: HistogramData;
        cls?: HistogramData;
        inp?: HistogramData;
      };
    };
    tablet_field_performance_metrics?: {
      histogram?: {
        lcp?: HistogramData;
        fid?: HistogramData;
        cls?: HistogramData;
        inp?: HistogramData;
      };
    };
    field_data_available?: boolean;
    mobile_field_data_available?: boolean;
    desktop_field_data_available?: boolean;
    tablet_field_data_available?: boolean;
  } | null;
  isLoading?: boolean;
}

export function PerformanceHistogramChart({ data, isLoading }: PerformanceHistogramChartProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5" />
            Real User Experience Distribution
          </CardTitle>
          <CardDescription>Loading Chrome UX Report histogram data...</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-64">
            <Activity className="h-8 w-8 animate-pulse text-muted-foreground" />
          </div>
        </CardContent>
      </Card>
    );
  }

  // Check if we have any histogram data
  const hasHistogramData = data?.mobile_field_performance_metrics?.histogram || 
                           data?.desktop_field_performance_metrics?.histogram ||
                           data?.tablet_field_performance_metrics?.histogram;

  if (!hasHistogramData) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5" />
            Real User Experience Distribution
          </CardTitle>
          <CardDescription>Chrome User Experience Report histogram data</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center h-64 space-y-3">
            <AlertCircle className="h-12 w-12 text-muted-foreground" />
            <div className="text-center">
              <p className="font-medium">No CrUX histogram data available</p>
              <p className="text-sm text-muted-foreground mt-1">
                This data requires real user traffic and sufficient volume in Chrome User Experience Report
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  const processHistogramData = (histogram: Record<string, HistogramData>, metricName: string) => {
    return Object.entries(histogram).map(([metric, data]) => ({
      metric: metric.toUpperCase(),
      Good: Math.round(data.good || 0),
      'Needs Improvement': Math.round(data.needs_improvement || 0),
      Poor: Math.round(data.poor || 0)
    }));
  };

  const renderHistogramChart = (histogramData: Record<string, HistogramData>, title: string) => {
    const chartData = processHistogramData(histogramData, title);
    
    if (chartData.length === 0) {
      return (
        <div className="flex items-center justify-center h-64 text-muted-foreground">
          No histogram data available
        </div>
      );
    }

    const colors = {
      Good: '#22c55e',
      'Needs Improvement': '#f59e0b', 
      Poor: '#ef4444'
    };

    return (
      <div className="space-y-4">
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis 
                dataKey="metric" 
                className="text-xs"
              />
              <YAxis 
                className="text-xs"
                label={{ value: '% of experiences', angle: -90, position: 'insideLeft' }}
              />
              <Tooltip
                contentStyle={{ 
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px'
                }}
                formatter={(value: number, name: string) => [
                  `${value}%`, 
                  name
                ]}
              />
              <Legend />
              <Bar dataKey="Good" stackId="a" fill={colors.Good} radius={[0, 0, 0, 0]} />
              <Bar dataKey="Needs Improvement" stackId="a" fill={colors['Needs Improvement']} radius={[0, 0, 0, 0]} />
              <Bar dataKey="Poor" stackId="a" fill={colors.Poor} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Summary cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {chartData.map((item) => {
            const goodPercentage = item.Good;
            const needsImprovementPercentage = item['Needs Improvement'];
            const poorPercentage = item.Poor;
            const totalExperiences = goodPercentage + needsImprovementPercentage + poorPercentage;
            
            // Get the dominant category
            const categories = [
              { name: 'Good', value: goodPercentage, color: 'text-green-600' },
              { name: 'Needs Improvement', value: needsImprovementPercentage, color: 'text-yellow-600' },
              { name: 'Poor', value: poorPercentage, color: 'text-red-600' }
            ];
            const dominant = categories.reduce((prev, current) => 
              current.value > prev.value ? current : prev
            );

            return (
              <div key={item.metric} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-medium text-sm">{item.metric}</h4>
                  <Badge variant={
                    dominant.name === 'Good' ? 'default' : 
                    dominant.name === 'Needs Improvement' ? 'secondary' : 'destructive'
                  }>
                    {dominant.value}% {dominant.name}
                  </Badge>
                </div>
                <div className="space-y-1 text-xs">
                  <div className="flex justify-between">
                    <span className="text-green-600">Good:</span>
                    <span>{goodPercentage}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-yellow-600">Needs Improvement:</span>
                    <span>{needsImprovementPercentage}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-red-600">Poor:</span>
                    <span>{poorPercentage}%</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Users className="h-5 w-5" />
          Real User Experience Distribution
        </CardTitle>
        <CardDescription>
          Chrome User Experience Report histogram showing the distribution of real user experiences
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="mobile" className="space-y-4">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="mobile" disabled={!data?.mobile_field_performance_metrics?.histogram}>
              <Smartphone className="mr-1 h-3 w-3" />
              Mobile Users
            </TabsTrigger>
            <TabsTrigger value="desktop" disabled={!data?.desktop_field_performance_metrics?.histogram}>
              <Monitor className="mr-1 h-3 w-3" />
              Desktop Users
            </TabsTrigger>
            <TabsTrigger value="tablet" disabled={!data?.tablet_field_performance_metrics?.histogram}>
              <Tablet className="mr-1 h-3 w-3" />
              Tablet Users
            </TabsTrigger>
          </TabsList>

          <TabsContent value="mobile">
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Activity className="h-4 w-4" />
                Real user experience data from mobile devices
              </div>
              {data?.mobile_field_performance_metrics?.histogram ? 
                renderHistogramChart(data.mobile_field_performance_metrics.histogram, 'Mobile') :
                <div className="text-center text-muted-foreground py-8">
                  No mobile histogram data available
                </div>
              }
            </div>
          </TabsContent>

          <TabsContent value="desktop">
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Activity className="h-4 w-4" />
                Real user experience data from desktop devices
              </div>
              {data?.desktop_field_performance_metrics?.histogram ? 
                renderHistogramChart(data.desktop_field_performance_metrics.histogram, 'Desktop') :
                <div className="text-center text-muted-foreground py-8">
                  No desktop histogram data available
                </div>
              }
            </div>
          </TabsContent>

          <TabsContent value="tablet">
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Activity className="h-4 w-4" />
                Real user experience data from tablet devices
              </div>
              {data?.tablet_field_performance_metrics?.histogram ? 
                renderHistogramChart(data.tablet_field_performance_metrics.histogram, 'Tablet') :
                <div className="text-center text-muted-foreground py-8">
                  No tablet histogram data available
                </div>
              }
            </div>
          </TabsContent>
        </Tabs>

        {/* Information about the data */}
        <div className="mt-6 p-4 bg-muted/50 rounded-lg">
          <h4 className="font-medium text-sm mb-2">About this data</h4>
          <ul className="text-xs text-muted-foreground space-y-1">
            <li>• Data comes from real Chrome users who opted-in to usage statistics</li>
            <li>• Percentages show the distribution of user experiences across performance categories</li>
            <li>• &quot;Good&quot; experiences meet Google&apos;s recommended thresholds for Core Web Vitals</li>
            <li>• Data is aggregated over a 28-day rolling period</li>
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}