'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  FileText, 
  AlertTriangle, 
  CheckCircle, 
  XCircle, 
  ExternalLink,
  Search,
  Activity,
  Target,
  Hash,
  Image,
  Link,
  RefreshCw
} from 'lucide-react';
import { api } from '@/lib/api-client';
import { useQuery } from '@tanstack/react-query';

interface TitleAnalysis {
  title: string;
  length: number;
  is_present: boolean;
  is_optimal_length: boolean;
  recommendations: string[];
}

interface MetaAnalysis {
  meta_description: string;
  meta_keywords: string;
  robots: string;
  description_length: number;
  has_description: boolean;
  is_optimal_description_length: boolean;
  recommendations: string[];
}

interface HeadingAnalysis {
  headings: Record<string, string[]>;
  h1_count: number;
  has_h1: boolean;
  proper_structure: boolean;
  recommendations: string[];
}

interface ContentAnalysis {
  word_count: number;
  text_to_html_ratio: number;
  readability_score: number;
  keyword_density: Record<string, number>;
  recommendations: string[];
}

interface LinkAnalysis {
  internal_links: number;
  external_links: number;
  broken_links: number;
  nofollow_links: number;
  recommendations: string[];
}

interface ImageAnalysis {
  total_images: number;
  images_without_alt: number;
  images_without_title: number;
  alt_text_coverage: number;
  recommendations: string[];
}

interface SEOAnalysisData {
  url: string;
  seo_score: number;
  title_analysis: TitleAnalysis;
  meta_analysis: MetaAnalysis;
  heading_analysis: HeadingAnalysis;
  content_analysis: ContentAnalysis;
  link_analysis: LinkAnalysis;
  image_analysis: ImageAnalysis;
}

interface SEOAnalysisChartProps {
  url: string;
  className?: string;
}

function getScoreColor(score: number): string {
  if (score >= 80) return 'text-green-600';
  if (score >= 60) return 'text-yellow-600';
  return 'text-red-600';
}

function getScoreBadgeVariant(score: number): 'default' | 'secondary' | 'destructive' {
  if (score >= 80) return 'default';
  if (score >= 60) return 'secondary';
  return 'destructive';
}

export function SEOAnalysisChart({ url, className = '' }: SEOAnalysisChartProps) {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisProgress, setAnalysisProgress] = useState(0);
  const [currentStage, setCurrentStage] = useState<string>('');

  // Query for SEO analysis data
  const { data: seoData, isLoading, error, refetch } = useQuery({
    queryKey: ['seo-analysis', url],
    queryFn: async () => {
      if (!url) return null;
      const response = await api.diagnostic.analyzeSeo(url);
      return response.data as SEOAnalysisData;
    },
    enabled: false, // Only run when manually triggered
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  const handleAnalyze = async () => {
    setIsAnalyzing(true);
    setAnalysisProgress(0);
    setCurrentStage('Initializing analysis...');
    
    try {
      // Simulate progressive analysis stages
      const stages = [
        { stage: 'Fetching page content...', progress: 20 },
        { stage: 'Analyzing HTML structure...', progress: 40 },
        { stage: 'Checking meta tags...', progress: 60 },
        { stage: 'Analyzing content quality...', progress: 80 },
        { stage: 'Generating recommendations...', progress: 95 },
        { stage: 'Analysis complete!', progress: 100 }
      ];
      
      for (const { stage, progress } of stages) {
        setCurrentStage(stage);
        setAnalysisProgress(progress);
        await new Promise(resolve => setTimeout(resolve, 800)); // Simulate work
      }
      
      await refetch();
    } finally {
      setIsAnalyzing(false);
      setAnalysisProgress(0);
      setCurrentStage('');
    }
  };

  if (error) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="h-5 w-5" />
            SEO Analysis
          </CardTitle>
          <CardDescription>Failed to analyze SEO for this URL</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-[200px] text-muted-foreground">
            <div className="text-center">
              <XCircle className="h-8 w-8 mx-auto mb-2" />
              <p>Analysis failed</p>
              <Button variant="outline" onClick={handleAnalyze} className="mt-2">
                Try Again
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (isLoading || isAnalyzing) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="h-5 w-5" />
            SEO Analysis
            {isAnalyzing && (
              <Badge variant="secondary" className="animate-pulse">
                Analyzing...
              </Badge>
            )}
          </CardTitle>
          <CardDescription>
            {isAnalyzing ? currentStage : 'Loading SEO analysis data...'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isAnalyzing && (
            <div className="space-y-4 mb-6">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium">{currentStage}</span>
                <span className="text-muted-foreground">{analysisProgress}%</span>
              </div>
              <Progress value={analysisProgress} className="h-2" />
              
              {/* Progress stages indicator */}
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div className={`text-center p-2 rounded ${analysisProgress >= 40 ? 'bg-green-100 text-green-700' : 'bg-gray-100'}`}>
                  HTML Structure
                </div>
                <div className={`text-center p-2 rounded ${analysisProgress >= 60 ? 'bg-green-100 text-green-700' : 'bg-gray-100'}`}>
                  Meta Analysis
                </div>
                <div className={`text-center p-2 rounded ${analysisProgress >= 80 ? 'bg-green-100 text-green-700' : 'bg-gray-100'}`}>
                  Content Quality
                </div>
              </div>
            </div>
          )}
          
          <div className="space-y-4">
            <Skeleton className="h-8 w-full" />
            <div className="grid gap-4 md:grid-cols-2">
              <Skeleton className="h-32" />
              <Skeleton className="h-32" />
            </div>
            <Skeleton className="h-40 w-full" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!seoData) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="h-5 w-5" />
            SEO Analysis
          </CardTitle>
          <CardDescription>Analyze your page&apos;s SEO performance and get optimization recommendations</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-[200px] text-muted-foreground">
            <div className="text-center">
              <Activity className="h-8 w-8 mx-auto mb-2" />
              <p>Click below to start SEO analysis</p>
              <Button onClick={handleAnalyze} className="mt-4">
                <Search className="mr-2 h-4 w-4" />
                Analyze SEO
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Search className="h-5 w-5" />
              SEO Analysis
            </CardTitle>
            <CardDescription>
              Comprehensive SEO analysis and optimization recommendations
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={getScoreBadgeVariant(seoData.seo_score)}>
              SEO Score: {seoData.seo_score}/100
            </Badge>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={handleAnalyze}
              disabled={isAnalyzing}
            >
              {isAnalyzing ? (
                <>
                  <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <Search className="mr-2 h-4 w-4" />
                  Re-analyze
                </>
              )}
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="title-meta" className="space-y-4">
          <TabsList>
            <TabsTrigger value="title-meta">Title & Meta</TabsTrigger>
            <TabsTrigger value="headings">Headings</TabsTrigger>
            <TabsTrigger value="content">Content</TabsTrigger>
            <TabsTrigger value="links">Links</TabsTrigger>
            <TabsTrigger value="images">Images</TabsTrigger>
          </TabsList>

          <TabsContent value="title-meta" className="space-y-4">
            <div className="grid gap-6 md:grid-cols-2">
              {/* Title Analysis */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base flex items-center gap-2">
                    <FileText className="h-4 w-4" />
                    Title Tag Analysis
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium">Title Present</span>
                      {seoData.title_analysis.is_present ? (
                        <CheckCircle className="h-4 w-4 text-green-600" />
                      ) : (
                        <XCircle className="h-4 w-4 text-red-600" />
                      )}
                    </div>
                    {seoData.title_analysis.title && (
                      <p className="text-sm text-muted-foreground bg-gray-50 p-2 rounded">
                        &quot;{seoData.title_analysis.title}&quot;
                      </p>
                    )}
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium">Title Length</span>
                      <span className="text-sm font-bold">
                        {seoData.title_analysis.length} characters
                      </span>
                    </div>
                    <Progress 
                      value={Math.min((seoData.title_analysis.length / 60) * 100, 100)} 
                      className="h-2"
                    />
                    <div className="flex justify-between text-xs text-muted-foreground mt-1">
                      <span>0</span>
                      <span>30-60 optimal</span>
                      <span>60+</span>
                    </div>
                  </div>

                  {seoData.title_analysis.recommendations.length > 0 && (
                    <div>
                      <p className="text-sm font-medium mb-2">Recommendations:</p>
                      <ul className="text-sm text-muted-foreground space-y-1">
                        {seoData.title_analysis.recommendations.map((rec, idx) => (
                          <li key={idx} className="flex items-start gap-2">
                            <AlertTriangle className="h-3 w-3 text-yellow-600 mt-0.5 flex-shrink-0" />
                            {rec}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Meta Description Analysis */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Target className="h-4 w-4" />
                    Meta Description Analysis
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium">Description Present</span>
                      {seoData.meta_analysis.has_description ? (
                        <CheckCircle className="h-4 w-4 text-green-600" />
                      ) : (
                        <XCircle className="h-4 w-4 text-red-600" />
                      )}
                    </div>
                    {seoData.meta_analysis.meta_description && (
                      <p className="text-sm text-muted-foreground bg-gray-50 p-2 rounded">
                        &quot;{seoData.meta_analysis.meta_description}&quot;
                      </p>
                    )}
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium">Description Length</span>
                      <span className="text-sm font-bold">
                        {seoData.meta_analysis.description_length} characters
                      </span>
                    </div>
                    <Progress 
                      value={Math.min((seoData.meta_analysis.description_length / 160) * 100, 100)} 
                      className="h-2"
                    />
                    <div className="flex justify-between text-xs text-muted-foreground mt-1">
                      <span>0</span>
                      <span>120-160 optimal</span>
                      <span>160+</span>
                    </div>
                  </div>

                  {seoData.meta_analysis.robots && (
                    <div>
                      <p className="text-sm font-medium mb-2">Robots Meta Tag:</p>
                      <div className="space-y-2">
                        <Badge variant="outline" className="font-mono text-xs">
                          {seoData.meta_analysis.robots}
                        </Badge>
                        <div className="text-xs text-muted-foreground">
                          {seoData.meta_analysis.robots.includes('noindex') && (
                            <div className="flex items-center gap-1 text-red-600">
                              <XCircle className="h-3 w-3" />
                              Page is set to NOINDEX - will not be indexed by search engines
                            </div>
                          )}
                          {seoData.meta_analysis.robots.includes('nofollow') && (
                            <div className="flex items-center gap-1 text-yellow-600">
                              <AlertTriangle className="h-3 w-3" />
                              Page is set to NOFOLLOW - links will not pass SEO authority
                            </div>
                          )}
                          {seoData.meta_analysis.robots.includes('index') && !seoData.meta_analysis.robots.includes('noindex') && (
                            <div className="flex items-center gap-1 text-green-600">
                              <CheckCircle className="h-3 w-3" />
                              Page is indexable by search engines
                            </div>
                          )}
                          {seoData.meta_analysis.robots.includes('follow') && !seoData.meta_analysis.robots.includes('nofollow') && (
                            <div className="flex items-center gap-1 text-green-600">
                              <CheckCircle className="h-3 w-3" />
                              Links are followed by search engines
                            </div>
                          )}
                          {seoData.meta_analysis.robots.includes('noarchive') && (
                            <div className="flex items-center gap-1 text-blue-600">
                              <AlertTriangle className="h-3 w-3" />
                              Page will not be cached by search engines
                            </div>
                          )}
                          {seoData.meta_analysis.robots.includes('nosnippet') && (
                            <div className="flex items-center gap-1 text-blue-600">
                              <AlertTriangle className="h-3 w-3" />
                              Snippets will not be shown in search results
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )}

                  {seoData.meta_analysis.recommendations.length > 0 && (
                    <div>
                      <p className="text-sm font-medium mb-2">Recommendations:</p>
                      <ul className="text-sm text-muted-foreground space-y-1">
                        {seoData.meta_analysis.recommendations.map((rec, idx) => (
                          <li key={idx} className="flex items-start gap-2">
                            <AlertTriangle className="h-3 w-3 text-yellow-600 mt-0.5 flex-shrink-0" />
                            {rec}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="headings" className="space-y-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <Hash className="h-4 w-4" />
                  Heading Structure (H1-H6)
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium">H1 Tags Found</span>
                      <span className="text-sm font-bold">{seoData.heading_analysis.h1_count}</span>
                    </div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium">Proper Structure</span>
                      {seoData.heading_analysis.proper_structure ? (
                        <CheckCircle className="h-4 w-4 text-green-600" />
                      ) : (
                        <XCircle className="h-4 w-4 text-red-600" />
                      )}
                    </div>
                  </div>
                  
                  <div className="space-y-2">
                    {Object.entries(seoData.heading_analysis.headings).map(([level, headings]) => (
                      headings.length > 0 && (
                        <div key={level}>
                          <span className="text-sm font-medium">{level.toUpperCase()}: </span>
                          <span className="text-sm text-muted-foreground">{headings.length} found</span>
                        </div>
                      )
                    ))}
                  </div>
                </div>

                {seoData.heading_analysis.recommendations.length > 0 && (
                  <div>
                    <p className="text-sm font-medium mb-2">Recommendations:</p>
                    <ul className="text-sm text-muted-foreground space-y-1">
                      {seoData.heading_analysis.recommendations.map((rec, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <AlertTriangle className="h-3 w-3 text-yellow-600 mt-0.5 flex-shrink-0" />
                          {rec}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="content" className="space-y-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Content Analysis</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-3">
                  <div className="text-center p-4 border rounded-lg">
                    <p className="text-2xl font-bold">{seoData.content_analysis.word_count}</p>
                    <p className="text-sm text-muted-foreground">Words</p>
                  </div>
                  <div className="text-center p-4 border rounded-lg">
                    <p className="text-2xl font-bold">{seoData.content_analysis.text_to_html_ratio}%</p>
                    <p className="text-sm text-muted-foreground">Text/HTML Ratio</p>
                  </div>
                  <div className="text-center p-4 border rounded-lg">
                    <p className="text-2xl font-bold">{seoData.content_analysis.readability_score}</p>
                    <p className="text-sm text-muted-foreground">Readability</p>
                  </div>
                </div>

                {seoData.content_analysis.recommendations.length > 0 && (
                  <div>
                    <p className="text-sm font-medium mb-2">Recommendations:</p>
                    <ul className="text-sm text-muted-foreground space-y-1">
                      {seoData.content_analysis.recommendations.map((rec, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <AlertTriangle className="h-3 w-3 text-yellow-600 mt-0.5 flex-shrink-0" />
                          {rec}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="links" className="space-y-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <Link className="h-4 w-4" />
                  Link Analysis
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm">Internal Links:</span>
                      <span className="font-medium">{seoData.link_analysis.internal_links}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm">External Links:</span>
                      <span className="font-medium">{seoData.link_analysis.external_links}</span>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm">Broken Links:</span>
                      <span className="font-medium text-red-600">{seoData.link_analysis.broken_links}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm">NoFollow Links:</span>
                      <span className="font-medium">{seoData.link_analysis.nofollow_links}</span>
                    </div>
                  </div>
                </div>

                {seoData.link_analysis.recommendations.length > 0 && (
                  <div>
                    <p className="text-sm font-medium mb-2">Recommendations:</p>
                    <ul className="text-sm text-muted-foreground space-y-1">
                      {seoData.link_analysis.recommendations.map((rec, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <AlertTriangle className="h-3 w-3 text-yellow-600 mt-0.5 flex-shrink-0" />
                          {rec}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="images" className="space-y-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <Image className="h-4 w-4" aria-label="Image optimization" />
                  Image Optimization
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm">Total Images:</span>
                      <span className="font-medium">{seoData.image_analysis.total_images}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm">Missing Alt Text:</span>
                      <span className="font-medium text-red-600">{seoData.image_analysis.images_without_alt}</span>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm">Alt Text Coverage:</span>
                      <span className="font-medium">{seoData.image_analysis.alt_text_coverage}%</span>
                    </div>
                    <Progress value={seoData.image_analysis.alt_text_coverage} className="h-2" />
                  </div>
                </div>

                {seoData.image_analysis.recommendations.length > 0 && (
                  <div>
                    <p className="text-sm font-medium mb-2">Recommendations:</p>
                    <ul className="text-sm text-muted-foreground space-y-1">
                      {seoData.image_analysis.recommendations.map((rec, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <AlertTriangle className="h-3 w-3 text-yellow-600 mt-0.5 flex-shrink-0" />
                          {rec}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}