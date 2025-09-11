'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import Image from 'next/image'; // <-- CHANGE #1: Imported Next.js Image component
import { useRouter } from 'next/navigation';
import { MagneticButton } from '@/components/ui/magnetic-button';
import { CTAButton } from '@/components/ui/cta-button';
import { SimpleMagneticWrapper } from '@/components/ui/simple-magnetic-wrapper';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { SEOOrb } from '@/components/ui/seo-orb';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Activity,
  AlertCircle,
  ArrowRight,
  BarChart3,
  BookOpen,
  Brain,
  Building2,
  Calendar,
  CheckCircle,
  CheckCircle2,
  ChevronRight,
  Clock,
  Cloud,
  Code,
  Cpu,
  Database,
  DollarSign,
  Download,
  Eye,
  FileText,
  Filter,
  Gauge,
  GitBranch,
  Globe,
  Layers,
  LayoutDashboard,
  LineChart,
  Link2,
  Lock,
  MessageSquare,
  Microscope,
  MousePointer,
  Network,
  Package,
  Palette,
  PenTool,
  Phone,
  PieChart,
  Play,
  Plug,
  Plus,
  RefreshCw,
  Rocket,
  Scale,
  Search,
  Server,
  Settings,
  Share2,
  Shield,
  ShoppingCart,
  Signal,
  Sliders,
  Smartphone,
  Sparkles,
  Star,
  Tag,
  Target,
  Terminal,
  TestTube,
  Timer,
  TrendingUp,
  Tv,
  Upload,
  UserCheck,
  Users,
  Video,
  Wand2,
  Wifi,
  Workflow,
  X,
  Youtube,
  Zap,
} from 'lucide-react';
import { motion, useScroll, useTransform } from 'framer-motion';
import { useInView } from 'react-intersection-observer';

// Animation variants
const fadeInUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 }
};

const staggerChildren = {
  visible: {
    transition: {
      staggerChildren: 0.1
    }
  }
};

// Feature categories with detailed capabilities
const featureCategories = [
  {
    id: 'diagnostics',
    title: 'SEO Diagnostics & Monitoring',
    icon: Activity,
    description: 'Comprehensive site health analysis and real-time monitoring',
    features: [
      {
        name: 'Technical SEO Audit',
        description: '200+ automated checks for technical issues',
        capabilities: [
          'Page speed analysis',
          'Mobile responsiveness',
          'Crawlability checks',
          'XML sitemap validation',
          'Robots.txt analysis',
          'Schema markup validation',
        ],
      },
      {
        name: 'Real-time Monitoring',
        description: 'Continuous tracking of critical SEO metrics',
        capabilities: [
          '24/7 uptime monitoring',
          'Performance alerts',
          'Ranking fluctuations',
          'Index status tracking',
          'Core Web Vitals',
          'Custom alert rules',
        ],
      },
      {
        name: 'Competitive Analysis',
        description: 'Deep insights into competitor strategies',
        capabilities: [
          'Competitor tracking',
          'Gap analysis',
          'Backlink comparison',
          'Content opportunities',
          'SERP feature tracking',
          'Market share analysis',
        ],
      },
    ],
  },
  {
    id: 'profitability',
    title: 'Profitability & ROI Tracking',
    icon: TrendingUp,
    description: 'Transform SEO metrics into business intelligence',
    features: [
      {
        name: 'Revenue Attribution',
        description: 'Connect SEO efforts directly to revenue',
        capabilities: [
          'Traffic value calculation',
          'Conversion tracking',
          'Goal value mapping',
          'Customer lifetime value',
          'Channel attribution',
          'Revenue forecasting',
        ],
      },
      {
        name: 'Cost Analysis',
        description: 'Track and optimize SEO investment',
        capabilities: [
          'Resource allocation',
          'Time tracking',
          'Tool cost management',
          'Opportunity cost analysis',
          'Budget optimization',
          'Team productivity',
        ],
      },
      {
        name: 'ROI Dashboard',
        description: 'Executive-ready reporting and insights',
        capabilities: [
          'Custom KPI tracking',
          'Automated reporting',
          'Trend analysis',
          'Predictive modeling',
          'Scenario planning',
          'Export capabilities',
        ],
      },
    ],
  },
  {
    id: 'ai-market',
    title: 'AI Market Simulation',
    icon: Brain,
    description: 'Predictive analytics and market intelligence',
    features: [
      {
        name: 'Predictive Analytics',
        description: 'AI-powered forecasting and insights',
        capabilities: [
          'Traffic predictions',
          'Ranking forecasts',
          'Seasonal trends',
          'Algorithm impact analysis',
          'Competitive movements',
          'Market opportunities',
        ],
      },
      {
        name: 'Scenario Planning',
        description: 'Test strategies before implementation',
        capabilities: [
          'What-if analysis',
          'Strategy simulation',
          'Risk assessment',
          'Resource planning',
          'Timeline projections',
          'Success probability',
        ],
      },
      {
        name: 'Market Intelligence',
        description: 'Stay ahead of industry changes',
        capabilities: [
          'Trend detection',
          'Industry benchmarks',
          'Emerging keywords',
          'User intent shifts',
          'SERP evolution',
          'Competitive alerts',
        ],
      },
    ],
  },
  {
    id: 'content',
    title: 'Content Workflow & Optimization',
    icon: FileText,
    description: 'Streamline content creation and optimization',
    features: [
      {
        name: 'AI Content Assistant',
        description: 'Intelligent content recommendations',
        capabilities: [
          'Topic suggestions',
          'Content briefs',
          'Optimization tips',
          'Readability analysis',
          'Keyword integration',
          'Meta generation',
        ],
      },
      {
        name: 'Workflow Management',
        description: 'Collaborative content pipeline',
        capabilities: [
          'Editorial calendar',
          'Task assignment',
          'Review workflows',
          'Version control',
          'Publishing automation',
          'Performance tracking',
        ],
      },
      {
        name: 'Content Analytics',
        description: 'Measure and improve content performance',
        capabilities: [
          'Engagement metrics',
          'Conversion tracking',
          'Content scoring',
          'A/B testing',
          'User behavior',
          'Content ROI',
        ],
      },
    ],
  },
  {
    id: 'sge',
    title: 'SGE Readiness & AI Optimization',
    icon: Sparkles,
    description: 'Prepare for the future of search',
    features: [
      {
        name: 'SGE Compatibility',
        description: 'Optimize for Search Generative Experience',
        capabilities: [
          'AI snapshot optimization',
          'Featured snippet targeting',
          'Conversational search',
          'Entity optimization',
          'Structured data',
          'Answer targeting',
        ],
      },
      {
        name: 'Voice Search Optimization',
        description: 'Capture voice and conversational queries',
        capabilities: [
          'Natural language processing',
          'Question targeting',
          'Local voice search',
          'Long-tail optimization',
          'Speakable markup',
          'Intent matching',
        ],
      },
      {
        name: 'AI-First Content',
        description: 'Create content for AI-powered search',
        capabilities: [
          'Semantic optimization',
          'Topic modeling',
          'Knowledge graphs',
          'FAQ generation',
          'Contextual relevance',
          'Multi-modal content',
        ],
      },
    ],
  },
  {
    id: 'knowledge',
    title: 'Knowledge Engine & Authority',
    icon: BookOpen,
    description: 'Build topical authority and expertise',
    features: [
      {
        name: 'Topic Clustering',
        description: 'Organize content for maximum impact',
        capabilities: [
          'Automatic clustering',
          'Pillar page identification',
          'Internal linking',
          'Content gaps',
          'Semantic relationships',
          'Authority scoring',
        ],
      },
      {
        name: 'E-E-A-T Optimization',
        description: 'Demonstrate expertise and trustworthiness',
        capabilities: [
          'Author profiles',
          'Credibility signals',
          'Trust factors',
          'Expert content',
          'Citation tracking',
          'Review management',
        ],
      },
      {
        name: 'Knowledge Graph',
        description: "Build your brand's knowledge presence",
        capabilities: [
          'Entity optimization',
          'Brand mentions',
          'Relationship mapping',
          'Schema generation',
          'Wikipedia presence',
          'Knowledge panels',
        ],
      },
    ],
  },
];

// Platform capabilities
const platformCapabilities = [
  {
    category: 'Data & Analytics',
    icon: Database,
    features: [
      'Unlimited data retention',
      'Custom data warehouse export',
      'Advanced segmentation',
      'Real-time processing',
      'Historical comparisons',
      'Predictive analytics',
    ],
  },
  {
    category: 'Integration & API',
    icon: Plug,
    features: [
      'RESTful API access',
      'Webhook notifications',
      'Native integrations',
      'Custom connectors',
      'Bulk data import/export',
      'SDK availability',
    ],
  },
  {
    category: 'Security & Compliance',
    icon: Shield,
    features: [
      'SOC 2 Type II certified',
      'GDPR compliant',
      'Data encryption at rest',
      'Role-based access control',
      'Audit logs',
      'SSO/SAML support',
    ],
  },
  {
    category: 'Collaboration',
    icon: Users,
    features: [
      'Unlimited team members',
      'Custom user roles',
      'Project workspaces',
      'Shared dashboards',
      'Comments & annotations',
      'Activity feeds',
    ],
  },
];

// Feature card component with enhanced animations
const FeatureCard = ({ feature, index, isExpanded, onToggle }: any) => {
  const [ref, inView] = useInView({ triggerOnce: true, threshold: 0.1 });
  
  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 50 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.6, delay: index * 0.1 }}
      whileHover={{ y: -5 }}
      className="group"
    >
      <Card className="overflow-hidden bg-card/80 backdrop-blur-sm border-border/50 hover:border-primary/50 transition-all duration-300 card-float">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/[0.02] via-accent/[0.02] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
        
        <CardHeader 
          className="cursor-pointer relative"
          onClick={onToggle}
        >
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-xl">{feature.name}</CardTitle>
              <CardDescription className="mt-2">{feature.description}</CardDescription>
            </div>
            <motion.div
              animate={{ rotate: isExpanded ? 90 : 0 }}
              transition={{ duration: 0.2 }}
            >
              <ChevronRight className="h-5 w-5 text-muted-foreground" />
            </motion.div>
          </div>
        </CardHeader>
        
        <motion.div
          initial={false}
          animate={{ height: isExpanded ? 'auto' : 0 }}
          transition={{ duration: 0.3 }}
          className="overflow-hidden"
        >
          <CardContent>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {feature.capabilities.map((capability: string, idx: number) => (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, x: -20 }}
                  animate={isExpanded ? { opacity: 1, x: 0 } : {}}
                  transition={{ delay: idx * 0.05 }}
                  className="flex items-start space-x-2"
                >
                  <CheckCircle2 className="h-5 w-5 text-accent mt-0.5 flex-shrink-0" />
                  <span className="text-sm">{capability}</span>
                </motion.div>
              ))}
            </div>
          </CardContent>
        </motion.div>
      </Card>
    </motion.div>
  );
};

export default function FeaturesPage() {
  const router = useRouter();
  const [selectedCategory, setSelectedCategory] = useState('diagnostics');
  const [expandedFeatures, setExpandedFeatures] = useState<string[]>([]);
  const [isScrolled, setIsScrolled] = useState(false);
  const { scrollY } = useScroll();
  
  // Parallax transforms
  const heroY = useTransform(scrollY, [0, 500], [0, 150]);
  const meshY = useTransform(scrollY, [0, 500], [0, -100]);
  const orbScale = useTransform(scrollY, [0, 500], [1, 0.8]);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 10);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const toggleFeature = (featureName: string) => {
    setExpandedFeatures(prev =>
      prev.includes(featureName)
        ? prev.filter(f => f !== featureName)
        : [...prev, featureName]
    );
  };

  const selectedCategoryData = featureCategories.find(cat => cat.id === selectedCategory);

  return (
    <div className="min-h-screen bg-background text-foreground relative noise-overlay">
      
      {/* Modern Navigation */}
      <nav className={`fixed top-0 w-full z-50 transition-all duration-500 ${
        isScrolled 
          ? 'bg-background/80 backdrop-blur-xl border-b border-border' 
          : 'bg-transparent'
      }`}>
        <div className="container-width px-6 mx-auto">
          <div className="flex items-center justify-between h-20">
            <div className="flex items-center space-x-12">
              <Link href="/" className="flex items-center space-x-3 group">
                <div className="relative w-10 h-10">
                  {/* CHANGE #2: Replaced <img> with <Image> */}
                  <Image src="/serptank-orb-enhanced.svg" alt="SerpTank" width={40} height={40} className="w-full h-full object-contain" />
                </div>
                <span className="text-2xl font-bold tracking-tight">SerpTank</span>
              </Link>
              <div className="hidden lg:flex items-center space-x-8">
                <Link
                  href="/"
                  className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors relative group"
                >
                  Home
                  <span className="absolute -bottom-1 left-0 w-0 h-0.5 bg-primary group-hover:w-full transition-all duration-300" />
                </Link>
                <Link
                  href="/features"
                  className="text-sm font-medium text-foreground relative group"
                >
                  Features
                  <span className="absolute -bottom-1 left-0 w-full h-0.5 bg-primary" />
                </Link>
                <Link
                  href="/pricing"
                  className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors relative group"
                >
                  Pricing
                  <span className="absolute -bottom-1 left-0 w-0 h-0.5 bg-primary group-hover:w-full transition-all duration-300" />
                </Link>
                <Link
                  href="/case-studies"
                  className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors relative group"
                >
                  Case Studies
                  <span className="absolute -bottom-1 left-0 w-0 h-0.5 bg-primary group-hover:w-full transition-all duration-300" />
                </Link>
                <Link
                  href="/about"
                  className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors relative group"
                >
                  About
                  <span className="absolute -bottom-1 left-0 w-0 h-0.5 bg-primary group-hover:w-full transition-all duration-300" />
                </Link>
              </div>
            </div>
            <div className="flex items-center space-x-6">
              <SimpleMagneticWrapper>
                <MagneticButton
                  variant="ghost"
                  size="sm"
                  onClick={() => router.push('/login')}
                  magneticStrength={0}
                >
                  Sign In
                </MagneticButton>
              </SimpleMagneticWrapper>
              <SimpleMagneticWrapper>
                <CTAButton
                  size="sm"
                  onClick={() => router.push('/register')}
                >
                  Start Free Trial
                  <ArrowRight className="ml-2 h-4 w-4" />
                </CTAButton>
              </SimpleMagneticWrapper>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section with Parallax */}
      <section className="relative min-h-[60vh] flex items-center justify-center overflow-hidden pt-20">
        {/* Background gradient mesh */}
        <motion.div 
          className="absolute inset-0 gradient-mesh opacity-20 dark:opacity-10"
          style={{ y: meshY }}
        />
        
        {/* Enhanced floating 3D orb */}
        <motion.div
          className="absolute right-[-200px] top-1/2 -translate-y-1/2 w-[800px] h-[800px] lg:w-[1000px] lg:h-[1000px]"
          style={{ y: heroY, scale: orbScale }}
        >
          <SEOOrb className="scale-150" colorTheme="green" />
        </motion.div>
        
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
        </div>
        
        <motion.div 
          className="container-width px-6 mx-auto text-center relative z-10"
          style={{ y: heroY }}
        >
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            <Badge variant="secondary" className="mb-6 animate-slide-up-fade">
              <Rocket className="mr-1 h-3 w-3" />
              Complete SEO Platform
            </Badge>
          </motion.div>
          
          <motion.h1 
            className="text-5xl sm:text-6xl md:text-7xl lg:text-8xl font-bold tracking-tighter mb-8 leading-[0.9]"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.1 }}
          >
            <span className="block">Every Tool You Need to</span>
            <span className="block text-gradient-electric mt-2">Dominate Search Results</span>
          </motion.h1>
          
          <motion.p 
            className="text-lg sm:text-xl md:text-2xl text-muted-foreground mb-12 max-w-3xl mx-auto leading-relaxed"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
          >
            From technical SEO to content optimization, profitability tracking to AI-powered insights.
            SerpTank provides a comprehensive suite of tools designed for enterprise success.
          </motion.p>
        </motion.div>
      </section>

      {/* Gradient divider */}
      <div className="h-px bg-gradient-to-r from-transparent via-border/50 to-transparent" />
      
      {/* Feature Categories Navigation - Enterprise Layout */}
      <section className="relative section-padding bg-slate-50/30 dark:bg-slate-950/30">
        <div className="container-width px-6 mx-auto">
          <div className="grid lg:grid-cols-3 gap-8">
            {/* Left Sidebar Navigation */}
            <div className="lg:col-span-1">
              <div className="sticky top-24">
                <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-4">
                  Feature Categories
                </h3>
                <nav className="space-y-2">
                  {featureCategories.map((category) => (
                    <button
                      key={category.id}
                      onClick={() => setSelectedCategory(category.id)}
                      className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition-all duration-200 ${
                        selectedCategory === category.id
                          ? 'bg-primary/10 text-primary border-l-4 border-primary'
                          : 'text-muted-foreground hover:text-foreground hover:bg-card/50'
                      }`}
                    >
                      <category.icon className={`h-5 w-5 ${
                        selectedCategory === category.id ? 'text-primary' : 'text-muted-foreground'
                      }`} />
                      <div className="text-left">
                        <div className="font-medium text-sm">{category.title}</div>
                        {selectedCategory === category.id && (
                          <div className="text-xs text-muted-foreground mt-0.5">
                            {category.features.length} capabilities
                          </div>
                        )}
                      </div>
                    </button>
                  ))}
                </nav>
              </div>
            </div>

            {/* Right Content Area */}
            <div className="lg:col-span-2">
              {selectedCategoryData && (
                <motion.div 
                  key={selectedCategory}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3 }}
                  className="space-y-8"
                >
                  {/* Category Header */}
                  <div>
                    <div className="flex items-center space-x-4 mb-4">
                      <div className="p-3 rounded-lg bg-primary/10">
                        <selectedCategoryData.icon className="h-6 w-6 text-primary" />
                      </div>
                      <div>
                        <h2 className="text-2xl font-bold">{selectedCategoryData.title}</h2>
                        <p className="text-muted-foreground">{selectedCategoryData.description}</p>
                      </div>
                    </div>
                  </div>

                  {/* Features Grid */}
                  <div className="grid gap-6">
                    {selectedCategoryData.features.map((feature, index) => (
                      <FeatureCard
                        key={feature.name}
                        feature={feature}
                        index={index}
                        isExpanded={expandedFeatures.includes(feature.name)}
                        onToggle={() => toggleFeature(feature.name)}
                      />
                    ))}
                  </div>
                </motion.div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Gradient divider */}
      <div className="h-px bg-gradient-to-r from-transparent via-border/50 to-transparent" />

      {/* Platform Capabilities with Enhanced Cards */}
      <section className="relative section-padding bg-gradient-to-b from-background via-background/95 to-background">
        <div className="container-width px-6 mx-auto">
          <motion.div 
            className="text-center mb-16"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <h2 className="text-4xl sm:text-5xl font-bold mb-6">
              <span className="text-gradient-neon">Enterprise-Grade</span> Platform
            </h2>
            <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
              Built on a foundation of reliability, security, and scalability
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {platformCapabilities.map((capability, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 50 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6, delay: index * 0.1 }}
                whileHover={{ y: -10 }}
                className="group"
              >
                <Card className="h-full bg-card/80 backdrop-blur-sm border-border/50 overflow-hidden card-float">
                  <div className="absolute inset-0 bg-gradient-to-br from-primary/[0.02] via-accent/[0.02] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                  
                  <CardHeader>
                    <div className="inline-flex items-center justify-center w-14 h-14 rounded-xl bg-primary/10 mb-4 group-hover:bg-primary/20 group-hover:scale-110 transition-all duration-300">
                      <capability.icon className="h-7 w-7 text-primary" />
                    </div>
                    <CardTitle className="text-xl">{capability.category}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-3">
                      {capability.features.map((feature, idx) => (
                        <motion.li 
                          key={idx} 
                          className="flex items-start text-sm"
                          initial={{ opacity: 0, x: -20 }}
                          whileInView={{ opacity: 1, x: 0 }}
                          viewport={{ once: true }}
                          transition={{ delay: index * 0.1 + idx * 0.05 }}
                        >
                          <CheckCircle2 className="h-4 w-4 text-accent mr-2 mt-0.5 flex-shrink-0" />
                          {feature}
                        </motion.li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Gradient divider */}
      <div className="h-px bg-gradient-to-r from-transparent via-border/50 to-transparent" />
      
      {/* Comparison Table with Modern Design */}
      <section className="relative section-padding bg-gray-50/40 dark:bg-gray-950/40">
        <div className="container-width px-6 mx-auto">
          <motion.div 
            className="text-center mb-16"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <h2 className="text-4xl sm:text-5xl font-bold mb-6">
              Why Choose <span className="text-gradient">SerpTank</span>?
            </h2>
            <p className="text-xl text-muted-foreground">
              See how we compare to other SEO platforms
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 50 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
          >
            <Card className="overflow-hidden bg-card/80 backdrop-blur-sm border-border/50">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-border/50">
                      <th className="text-left p-6 font-semibold">Feature</th>
                      <th className="text-center p-6">
                        <div className="flex items-center justify-center space-x-2">
                          <div className="relative">
                            <Zap className="h-6 w-6 text-primary relative z-10" />
                            <div className="absolute inset-0 bg-primary/20 blur-lg" />
                          </div>
                          <span className="font-bold text-lg">SerpTank</span>
                        </div>
                      </th>
                      <th className="text-center p-6 text-muted-foreground">Competitor A</th>
                      <th className="text-center p-6 text-muted-foreground">Competitor B</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      'AI-Powered Insights',
                      'Profitability Tracking',
                      'SGE Optimization',
                      'Real-time Monitoring',
                      'Unlimited Users',
                      'API Access',
                      'Custom Reporting',
                      'White-label Options',
                      '24/7 Support',
                      'Data Export',
                    ].map((feature, index) => (
                      <motion.tr 
                        key={index} 
                        className="border-b border-border/30 hover:bg-card/50 transition-colors"
                        initial={{ opacity: 0 }}
                        whileInView={{ opacity: 1 }}
                        viewport={{ once: true }}
                        transition={{ delay: index * 0.05 }}
                      >
                        <td className="p-6">{feature}</td>
                        <td className="text-center p-6">
                          <div className="inline-flex items-center justify-center">
                            <CheckCircle2 className="h-6 w-6 text-accent" />
                          </div>
                        </td>
                        <td className="text-center p-6">
                          {index % 3 === 0 ? (
                            <X className="h-6 w-6 text-muted-foreground/50 mx-auto" />
                          ) : (
                            <CheckCircle2 className="h-6 w-6 text-muted-foreground mx-auto" />
                          )}
                        </td>
                        <td className="text-center p-6">
                          {index % 2 === 0 ? (
                            <CheckCircle2 className="h-6 w-6 text-muted-foreground mx-auto" />
                          ) : (
                            <X className="h-6 w-6 text-muted-foreground/50 mx-auto" />
                          )}
                        </td>
                      </motion.tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </motion.div>
        </div>
      </section>

      {/* Gradient divider */}
      <div className="h-px bg-gradient-to-r from-transparent via-border/50 to-transparent" />

      {/* CTA Section with Gradient Background */}
      <section className="relative section-padding overflow-hidden">
        {/* Gradient background */}
        <div className="absolute inset-0">
          <div className="absolute inset-0 bg-gradient-to-r from-primary/5 via-accent/5 to-destructive/5" />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,hsl(var(--background))_50%)]" />
        </div>
        
        <motion.div
          className="container-width px-6 mx-auto text-center relative z-10"
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
        >
          <h2 className="text-4xl sm:text-5xl md:text-6xl font-bold mb-6">
            Experience the <span className="text-gradient-electric">Full Power</span> of SerpTank
          </h2>
          <p className="text-xl text-muted-foreground mb-12 max-w-2xl mx-auto">
            Get instant access to all features with our 14-day free trial
          </p>
          <div className="flex flex-col sm:flex-row gap-6 justify-center">
            <SimpleMagneticWrapper>
              <CTAButton
                size="xl"
                onClick={() => router.push('/register')}
              >
                Start Free Trial
                <ArrowRight className="ml-2 h-5 w-5" />
              </CTAButton>
            </SimpleMagneticWrapper>
            <SimpleMagneticWrapper>
              <MagneticButton
                variant="glass"
                size="xl"
                onClick={() => router.push('/demo')}
                className="text-xl"
                magneticStrength={0}
              >
                <Play className="mr-2 h-5 w-5" />
                Request Demo
              </MagneticButton>
            </SimpleMagneticWrapper>
          </div>
        </motion.div>
      </section>

      {/* Gradient divider */}
      <div className="h-px bg-gradient-to-r from-transparent via-border/50 to-transparent" />

      {/* Modern Footer */}
      <footer className="relative py-16 border-t border-border bg-slate-50/30 dark:bg-slate-950/30">
        <div className="container-width px-6 mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-8 lg:gap-12 mb-12">
            <div className="col-span-2">
              <div className="flex items-center space-x-3 mb-6">
                <div className="relative w-8 h-8">
                  {/* CHANGE #3: Replaced <img> with <Image> */}
                  <Image src="/serptank-orb-enhanced.svg" alt="SerpTank" width={32} height={32} className="w-full h-full object-contain" />
                </div>
                <span className="text-2xl font-bold">SerpTank</span>
              </div>
              <p className="text-muted-foreground mb-6 max-w-xs leading-relaxed">
                The AI-powered SEO platform that delivers real business results.
              </p>
              <div className="flex space-x-4">
                {[
                  { name: 'twitter', icon: 'X' },
                  { name: 'linkedin', icon: 'in' },
                  { name: 'github', icon: 'G' }
                ].map((social) => (
                  <a
                    key={social.name}
                    href={`https://${social.name}.com/serptank`}
                    className="w-10 h-10 rounded-full bg-card border border-border flex items-center justify-center hover:bg-primary/10 hover:border-primary/50 transition-all group"
                  >
                    <span className="sr-only">{social.name}</span>
                    <span className="text-sm font-bold text-muted-foreground group-hover:text-primary transition-colors">
                      {social.icon}
                    </span>
                  </a>
                ))}
              </div>
            </div>
            
            {[
              { title: 'Product', links: ['Features', 'Pricing', 'Changelog', 'Roadmap'] },
              { title: 'Company', links: ['About', 'Blog', 'Careers', 'Press'] },
              { title: 'Resources', links: ['Documentation', 'API', 'Status', 'Support'] },
            ].map((column, index) => (
              <div key={index}>
                <h3 className="font-semibold mb-4">{column.title}</h3>
                <ul className="space-y-2">
                  {column.links.map((link) => (
                    <li key={link}>
                      <Link
                        href={`/${link.toLowerCase()}`}
                        className="text-muted-foreground hover:text-foreground transition-colors"
                      >
                        {link}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          
          <div className="border-t border-border pt-8 flex flex-col md:flex-row justify-between items-center gap-4">
            <p className="text-sm text-muted-foreground order-2 md:order-1">
              © 2025 SerpTank. All rights reserved.
            </p>
            <div className="flex flex-wrap justify-center gap-6 order-1 md:order-2">
              <Link href="/privacy" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                Privacy
              </Link>
              <Link href="/terms" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                Terms
              </Link>
              <Link href="/security" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                Security
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}