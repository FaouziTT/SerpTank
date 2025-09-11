'use client';

import { MagneticButton } from '@/components/ui/magnetic-button';
import { FloatingCard, FeatureFloatingCard, MetricFloatingCard } from '@/components/ui/floating-card';
import { BentoGrid, BentoGridItem, BentoHero, BentoMetric, BentoFeature, BentoChart } from '@/components/ui/bento-grid';
import { Badge } from '@/components/ui/badge';
import { 
  Activity, 
  Brain, 
  DollarSign, 
  FileText, 
  Sparkles, 
  BookOpen,
  TrendingUp,
  Users,
  Globe,
  BarChart3,
  Zap,
  ArrowRight,
  CheckCircle2,
} from 'lucide-react';

export default function DesignShowcase() {
  const features = [
    {
      icon: Activity,
      title: 'AI-Powered Diagnostics',
      description: 'Real-time site analysis with machine learning insights',
      features: ['200+ automated checks', 'Predictive issue detection', 'Smart prioritization'],
    },
    {
      icon: Brain,
      title: 'Market Intelligence',
      description: 'Stay ahead with AI-driven competitive analysis',
      features: ['Competitor tracking', 'Trend prediction', 'Opportunity alerts'],
    },
    {
      icon: DollarSign,
      title: 'Revenue Attribution',
      description: 'Connect SEO directly to business outcomes',
      features: ['Revenue tracking', 'ROI calculation', 'Profit forecasting'],
    },
  ];

  const metrics = [
    { label: 'Active Users', value: '50K+', change: '+23%', icon: Users },
    { label: 'Websites Analyzed', value: '2M+', change: '+45%', icon: Globe },
    { label: 'Keywords Tracked', value: '10M+', change: '+67%', icon: BarChart3 },
    { label: 'Avg ROI', value: '312%', change: '+18%', icon: TrendingUp },
  ];

  return (
    <div className="min-h-screen bg-background text-foreground p-8">
      <div className="max-w-7xl mx-auto space-y-16">
        {/* Header */}
        <div className="text-center space-y-4">
          <Badge variant="secondary" className="mb-4">
            <Sparkles className="mr-1 h-3 w-3" />
            2025 Design System Showcase
          </Badge>
          <h1 className="text-6xl md:text-7xl font-bold tracking-tighter">
            <span className="text-gradient-electric">SerpTank</span> Design System
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Modern components built for the next generation of web applications
          </p>
        </div>

        {/* Magnetic Buttons Section */}
        <section className="space-y-8">
          <h2 className="text-4xl font-bold">Magnetic Buttons</h2>
          <div className="flex flex-wrap gap-4">
            <MagneticButton variant="primary" size="sm">
              Small Primary
            </MagneticButton>
            <MagneticButton variant="primary" size="md">
              Medium Primary
              <ArrowRight className="ml-2 h-4 w-4" />
            </MagneticButton>
            <MagneticButton variant="primary" size="lg">
              Large Primary
            </MagneticButton>
            <MagneticButton variant="primary" size="xl">
              Extra Large Primary
            </MagneticButton>
          </div>
          <div className="flex flex-wrap gap-4">
            <MagneticButton variant="secondary">
              Secondary Button
            </MagneticButton>
            <MagneticButton variant="ghost">
              Ghost Button
            </MagneticButton>
            <MagneticButton variant="neon">
              Neon Button
              <Sparkles className="ml-2 h-4 w-4" />
            </MagneticButton>
          </div>
        </section>

        {/* Floating Cards Section */}
        <section className="space-y-8">
          <h2 className="text-4xl font-bold">Floating Cards</h2>
          
          {/* Feature Cards */}
          <div className="grid md:grid-cols-3 gap-6">
            {features.map((feature, index) => (
              <FeatureFloatingCard
                key={index}
                icon={feature.icon}
                title={feature.title}
                description={feature.description}
                features={feature.features}
                index={index}
                glowColor={index === 0 ? 'primary' : index === 1 ? 'accent' : 'destructive'}
              />
            ))}
          </div>

          {/* Metric Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {metrics.map((metric, index) => (
              <MetricFloatingCard
                key={index}
                value={metric.value}
                label={metric.label}
                change={metric.change}
                icon={metric.icon}
                index={index}
              />
            ))}
          </div>
        </section>

        {/* Bento Grid Section */}
        <section className="space-y-8">
          <h2 className="text-4xl font-bold">Bento Grid Layout</h2>
          
          <BentoGrid>
            <BentoHero
              title="Transform your SEO"
              description="AI-powered insights that drive real business results"
              delay={0}
            >
              <MagneticButton variant="primary" size="lg">
                Get Started
                <ArrowRight className="ml-2 h-4 w-4" />
              </MagneticButton>
            </BentoHero>

            <BentoMetric
              value="98.5%"
              label="Uptime"
              icon={Activity}
              trend={{ value: '+0.5%', positive: true }}
              delay={0.1}
            />

            <BentoMetric
              value="234ms"
              label="Avg Response"
              icon={Zap}
              trend={{ value: '-12ms', positive: true }}
              delay={0.2}
            />

            <BentoFeature
              title="Smart Analytics"
              description="Get insights that matter with our AI-powered analytics engine"
              icon={Brain}
              delay={0.3}
            >
              <Badge variant="secondary">Coming Soon</Badge>
            </BentoFeature>

            <BentoChart
              title="Performance Trends"
              delay={0.4}
            >
              <div className="h-full bg-gradient-to-br from-primary/10 to-accent/10 rounded-lg flex items-center justify-center">
                <BarChart3 className="h-16 w-16 text-primary/30" />
              </div>
            </BentoChart>

            <BentoFeature
              title="Enterprise Security"
              description="Bank-level encryption and compliance"
              icon={BookOpen}
              delay={0.5}
            />
          </BentoGrid>
        </section>

        {/* Color Palette */}
        <section className="space-y-8">
          <h2 className="text-4xl font-bold">Color Palette</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="space-y-2">
              <div className="h-32 bg-primary rounded-lg"></div>
              <p className="font-semibold">Primary</p>
              <p className="text-sm text-muted-foreground">Electric Blue</p>
            </div>
            <div className="space-y-2">
              <div className="h-32 bg-accent rounded-lg"></div>
              <p className="font-semibold">Accent</p>
              <p className="text-sm text-muted-foreground">Neon Green</p>
            </div>
            <div className="space-y-2">
              <div className="h-32 bg-destructive rounded-lg"></div>
              <p className="font-semibold">Destructive</p>
              <p className="text-sm text-muted-foreground">Hot Pink</p>
            </div>
            <div className="space-y-2">
              <div className="h-32 bg-yellow-400 rounded-lg"></div>
              <p className="font-semibold">Warning</p>
              <p className="text-sm text-muted-foreground">Warm Yellow</p>
            </div>
          </div>
        </section>

        {/* Gradients */}
        <section className="space-y-8">
          <h2 className="text-4xl font-bold">Gradient Styles</h2>
          <div className="grid md:grid-cols-3 gap-4">
            <div className="h-32 rounded-lg gradient-mesh"></div>
            <div className="h-32 rounded-lg gradient-electric"></div>
            <div className="h-32 rounded-lg gradient-neon"></div>
          </div>
        </section>

        {/* Typography */}
        <section className="space-y-8">
          <h2 className="text-4xl font-bold">Typography Scale</h2>
          <div className="space-y-4">
            <h1 className="text-8xl font-bold">Heading 1</h1>
            <h2 className="text-6xl font-bold">Heading 2</h2>
            <h3 className="text-4xl font-semibold">Heading 3</h3>
            <h4 className="text-2xl font-semibold">Heading 4</h4>
            <h5 className="text-xl font-medium">Heading 5</h5>
            <h6 className="text-lg font-medium">Heading 6</h6>
            <p className="text-base">Body text with Inter font family</p>
            <p className="text-sm text-muted-foreground">Small muted text</p>
          </div>
        </section>

        {/* Animations */}
        <section className="space-y-8">
          <h2 className="text-4xl font-bold">Animation Classes</h2>
          <div className="flex flex-wrap gap-8">
            <div className="w-20 h-20 bg-primary rounded-lg animate-float"></div>
            <div className="w-20 h-20 bg-accent rounded-lg animate-glow-pulse"></div>
            <div className="w-20 h-20 bg-destructive rounded-lg animate-slide-up-fade"></div>
            <div className="w-20 h-20 bg-yellow-400 rounded-lg animate-scale-in"></div>
          </div>
        </section>
      </div>
    </div>
  );
}