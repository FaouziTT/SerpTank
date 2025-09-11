'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  ArrowRight,
  BarChart3,
  Brain,
  Building2,
  CheckCircle,
  ChevronRight,
  Clock,
  FileText,
  Globe,
  LineChart,
  Lock,
  Rocket,
  Search,
  Shield,
  Sparkles,
  TrendingUp,
  Users,
  Zap,
  Youtube,
  DollarSign,
  Target,
  Activity,
  Award,
  BookOpen,
  Briefcase,
  Cloud,
  Code,
  Coffee,
  Database,
  Gauge,
  GitBranch,
  Layers,
  LayoutDashboard,
  MessageSquare,
  Microscope,
  Network,
  PieChart,
  Play,
  Settings,
  Share2,
  Smartphone,
  Star,
  Terminal,
  Workflow,
  ArrowUpRight,
  CheckCircle2,
  CircleDollarSign,
  Cpu,
  Eye,
  Filter,
  Lightbulb,
  Link2,
  MapPin,
  Megaphone,
  MousePointer,
  Package,
  Palette,
  PenTool,
  Percent,
  Phone,
  Plug,
  PlusCircle,
  Presentation,
  Puzzle,
  Radio,
  RefreshCw,
  Repeat,
  Scale,
  ScanLine,
  Server,
  ShoppingCart,
  Signal,
  Sliders,
  Tag,
  TestTube,
  Timer,
  ToggleLeft,
  Trash2,
  TrendingDown,
  Tv,
  Upload,
  UserCheck,
  UserPlus,
  Video,
  Wand2,
  Wifi,
  Wind,
  X,
  Zap as ZapIcon,
} from 'lucide-react';
import { motion } from 'framer-motion';
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

// Enterprise metrics data
const metrics = [
  { label: 'Active Users', value: '50K+', growth: '+23%' },
  { label: 'Websites Analyzed', value: '2M+', growth: '+45%' },
  { label: 'Keywords Tracked', value: '10M+', growth: '+67%' },
  { label: 'ROI Improvement', value: '312%', growth: '+18%' },
];

// Core features
const coreFeatures = [
  {
    icon: Activity,
    title: 'SEO Diagnostics',
    description: 'Comprehensive site health analysis with actionable recommendations',
    benefits: ['200+ SEO checks', 'Real-time monitoring', 'Priority-based fixes'],
    color: 'text-blue-500',
    bgColor: 'bg-blue-50',
  },
  {
    icon: TrendingUp,
    title: 'Profitability Analysis',
    description: 'Transform SEO metrics into revenue projections and ROI calculations',
    benefits: ['Revenue forecasting', 'Cost-benefit analysis', 'ROI tracking'],
    color: 'text-green-500',
    bgColor: 'bg-green-50',
  },
  {
    icon: Brain,
    title: 'AI Market Simulation',
    description: 'Predict market changes and optimize strategies with AI-powered insights',
    benefits: ['Predictive analytics', 'Scenario planning', 'Risk assessment'],
    color: 'text-purple-500',
    bgColor: 'bg-purple-50',
  },
  {
    icon: FileText,
    title: 'Content Workflow',
    description: 'Streamline content creation with AI-assisted optimization',
    benefits: ['AI content suggestions', 'Workflow automation', 'Team collaboration'],
    color: 'text-orange-500',
    bgColor: 'bg-orange-50',
  },
  {
    icon: Sparkles,
    title: 'SGE Readiness',
    description: 'Prepare for Search Generative Experience with advanced optimization',
    benefits: ['SGE compatibility', 'Featured snippets', 'AI-first optimization'],
    color: 'text-pink-500',
    bgColor: 'bg-pink-50',
  },
  {
    icon: BookOpen,
    title: 'Knowledge Engine',
    description: 'Build topical authority with intelligent content mapping',
    benefits: ['Topic clustering', 'Authority scoring', 'Content gaps analysis'],
    color: 'text-indigo-500',
    bgColor: 'bg-indigo-50',
  },
];

// Enterprise features
const enterpriseFeatures = [
  { icon: Shield, label: 'Enterprise Security', description: 'SOC 2 compliant with advanced encryption' },
  { icon: Users, label: 'Team Collaboration', description: 'Unlimited users with role-based access' },
  { icon: GitBranch, label: 'API Integration', description: 'RESTful API with webhook support' },
  { icon: Database, label: 'Data Warehouse', description: 'Export to your data lake or warehouse' },
  { icon: Lock, label: 'SSO Support', description: 'SAML, OAuth, and custom SSO' },
  { icon: Phone, label: 'Priority Support', description: '24/7 dedicated support team' },
];

// Customer testimonials
const testimonials = [
  {
    quote: "SerpTank transformed our SEO strategy. We saw a 400% increase in organic traffic within 6 months.",
    author: "Sarah Chen",
    role: "VP of Marketing",
    company: "TechCorp Global",
    logo: "🏢",
    metrics: { traffic: '+400%', revenue: '+$2.3M', time: '6 months' }
  },
  {
    quote: "The AI-powered insights helped us stay ahead of algorithm changes and dominate our market.",
    author: "Michael Rodriguez",
    role: "Head of Digital",
    company: "E-commerce Giants",
    logo: "🛍️",
    metrics: { rankings: '#1 for 89%', conversion: '+67%', time: '4 months' }
  },
  {
    quote: "ROI tracking and profitability analysis justified our SEO investment to the C-suite.",
    author: "Jennifer Park",
    role: "CMO",
    company: "Finance Leaders Inc",
    logo: "💼",
    metrics: { roi: '312%', cost: '-45%', time: '3 months' }
  },
];

// Integration partners
const integrations = [
  { name: 'Google Search Console', icon: '🔍' },
  { name: 'Google Analytics', icon: '📊' },
  { name: 'Slack', icon: '💬' },
  { name: 'Salesforce', icon: '☁️' },
  { name: 'HubSpot', icon: '🧲' },
  { name: 'Zapier', icon: '⚡' },
  { name: 'Microsoft Teams', icon: '👥' },
  { name: 'Jira', icon: '🎯' },
];

export default function LandingPage() {
  const router = useRouter();
  const [isScrolled, setIsScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 10);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const [heroRef, heroInView] = useInView({ triggerOnce: true, threshold: 0.1 });
  const [featuresRef, featuresInView] = useInView({ triggerOnce: true, threshold: 0.1 });
  const [metricsRef, metricsInView] = useInView({ triggerOnce: true, threshold: 0.1 });
  const [enterpriseRef, enterpriseInView] = useInView({ triggerOnce: true, threshold: 0.1 });

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white dark:from-gray-950 dark:to-gray-900">
      {/* Navigation */}
      <nav className={`fixed top-0 w-full z-50 transition-all duration-300 ${
        isScrolled 
          ? 'bg-white dark:bg-gray-950 border-b border-gray-200 dark:border-gray-800 shadow-sm' 
          : 'bg-white/80 dark:bg-gray-950/80 backdrop-blur-md border-b border-gray-200/50 dark:border-gray-800/50'
      }`}>
        <div className="container mx-auto px-4">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-8">
              <Link href="/" className="flex items-center space-x-2">
                <Zap className="h-8 w-8 text-primary" />
                <span className="text-2xl font-bold">SerpTank</span>
              </Link>
              <div className="hidden md:flex items-center space-x-6">
                <Link href="/features" className="text-sm font-medium hover:text-primary transition-colors">
                  Features
                </Link>
                <Link href="/pricing" className="text-sm font-medium hover:text-primary transition-colors">
                  Pricing
                </Link>
                <Link href="/case-studies" className="text-sm font-medium hover:text-primary transition-colors">
                  Case Studies
                </Link>
                <Link href="/about" className="text-sm font-medium hover:text-primary transition-colors">
                  About
                </Link>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <Button variant="ghost" onClick={() => router.push('/login')}>
                Sign In
              </Button>
              <Button onClick={() => router.push('/register')}>
                Start Free Trial
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section ref={heroRef} className="relative pt-24 pb-20 px-4 overflow-hidden">
        {/* Background gradient */}
        <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-transparent pointer-events-none" />
        <div className="absolute top-0 right-0 w-96 h-96 bg-primary/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-primary/5 rounded-full blur-3xl pointer-events-none" />
        <motion.div 
          className="container mx-auto max-w-6xl text-center"
          initial="hidden"
          animate={heroInView ? "visible" : "hidden"}
          variants={staggerChildren}
        >
          <motion.div variants={fadeInUp} className="mb-6">
            <Badge variant="secondary" className="mb-4">
              <Sparkles className="mr-1 h-3 w-3" />
              AI-Powered SEO Platform
            </Badge>
          </motion.div>
          
          <motion.h1 
            variants={fadeInUp}
            className="text-5xl md:text-7xl font-bold tracking-tight mb-6 bg-gradient-to-r from-gray-900 to-gray-600 dark:from-gray-100 dark:to-gray-400 bg-clip-text text-transparent"
          >
            Turn SEO Data Into
            <br />
            Revenue Growth
          </motion.h1>
          
          <motion.p 
            variants={fadeInUp}
            className="text-xl text-muted-foreground mb-8 max-w-3xl mx-auto"
          >
            The enterprise SEO platform that combines advanced diagnostics, AI-powered insights, 
            and profitability tracking to deliver measurable business results.
          </motion.p>
          
          <motion.div variants={fadeInUp} className="flex flex-col sm:flex-row gap-4 justify-center mb-12">
            <Button size="lg" onClick={() => router.push('/register')}>
              Start 14-Day Free Trial
              <ArrowRight className="ml-2 h-5 w-5" />
            </Button>
            <Button size="lg" variant="outline" onClick={() => router.push('/features')}>
              <Play className="mr-2 h-5 w-5" />
              Watch Demo
            </Button>
          </motion.div>

          <motion.div variants={fadeInUp} className="grid grid-cols-2 md:grid-cols-4 gap-8 max-w-4xl mx-auto">
            {metrics.map((metric, index) => (
              <div key={index} className="text-center">
                <div className="text-3xl font-bold">{metric.value}</div>
                <div className="text-sm text-muted-foreground">{metric.label}</div>
                <Badge variant="secondary" className="mt-2">
                  <TrendingUp className="mr-1 h-3 w-3" />
                  {metric.growth}
                </Badge>
              </div>
            ))}
          </motion.div>
        </motion.div>
      </section>

      {/* Core Features Grid */}
      <section ref={featuresRef} className="relative py-20 px-4 bg-gradient-to-b from-gray-50 to-white dark:from-gray-900/50 dark:to-gray-950/30 border-y border-gray-200 dark:border-gray-800">
        <motion.div 
          className="container mx-auto max-w-7xl"
          initial="hidden"
          animate={featuresInView ? "visible" : "hidden"}
          variants={staggerChildren}
        >
          <motion.div variants={fadeInUp} className="text-center mb-12">
            <h2 className="text-4xl font-bold mb-4">Six Pillars of SEO Excellence</h2>
            <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
              Our comprehensive platform addresses every aspect of modern SEO, 
              from technical optimization to content strategy and market intelligence.
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {coreFeatures.map((feature, index) => (
              <motion.div key={index} variants={fadeInUp}>
                <Card className="h-full hover:shadow-lg transition-shadow">
                  <CardHeader>
                    <div className={`w-12 h-12 rounded-lg ${feature.bgColor} flex items-center justify-center mb-4`}>
                      <feature.icon className={`h-6 w-6 ${feature.color}`} />
                    </div>
                    <CardTitle>{feature.title}</CardTitle>
                    <CardDescription>{feature.description}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2">
                      {feature.benefits.map((benefit, idx) => (
                        <li key={idx} className="flex items-center text-sm">
                          <CheckCircle className="mr-2 h-4 w-4 text-green-500" />
                          {benefit}
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      {/* Interactive Demo Section */}
      <section className="py-20 px-4 bg-white dark:bg-gray-950">
        <div className="container mx-auto max-w-7xl">
          <div className="text-center mb-12">
            <h2 className="text-4xl font-bold mb-4">See SerpTank in Action</h2>
            <p className="text-xl text-muted-foreground">
              Explore our interactive dashboard and discover powerful insights
            </p>
          </div>

          <Card className="overflow-hidden">
            <Tabs defaultValue="dashboard" className="w-full">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="dashboard">Executive Dashboard</TabsTrigger>
                <TabsTrigger value="diagnostics">SEO Diagnostics</TabsTrigger>
                <TabsTrigger value="profitability">Profitability Tracking</TabsTrigger>
              </TabsList>
              
              <TabsContent value="dashboard" className="p-0">
                <div className="aspect-video bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-900 flex items-center justify-center">
                  <div className="text-center p-8">
                    <LayoutDashboard className="h-16 w-16 mx-auto mb-4 text-primary" />
                    <h3 className="text-2xl font-bold mb-2">Executive Dashboard</h3>
                    <p className="text-muted-foreground mb-4">
                      Real-time KPIs, performance trends, and actionable insights at a glance
                    </p>
                    <Button onClick={() => router.push('/register')}>
                      Try Interactive Demo
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </TabsContent>
              
              <TabsContent value="diagnostics" className="p-0">
                <div className="aspect-video bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-950 dark:to-blue-900 flex items-center justify-center">
                  <div className="text-center p-8">
                    <Activity className="h-16 w-16 mx-auto mb-4 text-blue-500" />
                    <h3 className="text-2xl font-bold mb-2">Comprehensive SEO Analysis</h3>
                    <p className="text-muted-foreground mb-4">
                      200+ automated checks with priority-based recommendations
                    </p>
                    <Button onClick={() => router.push('/register')}>
                      Start Free Analysis
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </TabsContent>
              
              <TabsContent value="profitability" className="p-0">
                <div className="aspect-video bg-gradient-to-br from-green-50 to-green-100 dark:from-green-950 dark:to-green-900 flex items-center justify-center">
                  <div className="text-center p-8">
                    <DollarSign className="h-16 w-16 mx-auto mb-4 text-green-500" />
                    <h3 className="text-2xl font-bold mb-2">ROI & Revenue Tracking</h3>
                    <p className="text-muted-foreground mb-4">
                      Connect SEO efforts directly to revenue impact and ROI
                    </p>
                    <Button onClick={() => router.push('/register')}>
                      Calculate Your ROI
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          </Card>
        </div>
      </section>

      {/* Enterprise Features */}
      <section ref={enterpriseRef} className="relative py-20 px-4 bg-gradient-to-b from-gray-50 to-gray-100 dark:from-gray-900/50 dark:to-gray-900/80 border-t border-gray-200 dark:border-gray-800">
        <motion.div 
          className="container mx-auto max-w-7xl"
          initial="hidden"
          animate={enterpriseInView ? "visible" : "hidden"}
          variants={staggerChildren}
        >
          <motion.div variants={fadeInUp} className="text-center mb-12">
            <Badge variant="secondary" className="mb-4">
              <Building2 className="mr-1 h-3 w-3" />
              Enterprise Ready
            </Badge>
            <h2 className="text-4xl font-bold mb-4">Built for Scale & Security</h2>
            <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
              Trusted by Fortune 500 companies and growing businesses alike
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
            {enterpriseFeatures.map((feature, index) => (
              <motion.div key={index} variants={fadeInUp}>
                <div className="flex items-start space-x-4">
                  <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                    <feature.icon className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <h3 className="font-semibold mb-1">{feature.label}</h3>
                    <p className="text-sm text-muted-foreground">{feature.description}</p>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>

          {/* Integration Partners */}
          <motion.div variants={fadeInUp} className="text-center">
            <h3 className="text-2xl font-bold mb-6">Seamless Integrations</h3>
            <div className="flex flex-wrap justify-center gap-4">
              {integrations.map((integration, index) => (
                <div key={index} className="flex items-center space-x-2 bg-white dark:bg-gray-800 rounded-lg px-4 py-2 shadow-sm">
                  <span className="text-2xl">{integration.icon}</span>
                  <span className="text-sm font-medium">{integration.name}</span>
                </div>
              ))}
            </div>
          </motion.div>
        </motion.div>
      </section>

      {/* Testimonials */}
      <section className="py-20 px-4 bg-white dark:bg-gray-950 relative">
        {/* Decorative element */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-px h-16 bg-gradient-to-b from-transparent via-gray-300 to-transparent dark:via-gray-700" />
        <div className="container mx-auto max-w-7xl">
          <div className="text-center mb-12">
            <h2 className="text-4xl font-bold mb-4">Trusted by Industry Leaders</h2>
            <p className="text-xl text-muted-foreground">
              See how companies achieve remarkable results with SerpTank
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {testimonials.map((testimonial, index) => (
              <Card key={index} className="hover:shadow-lg transition-shadow">
                <CardHeader>
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-4xl">{testimonial.logo}</span>
                    <Badge variant="secondary">
                      <Award className="mr-1 h-3 w-3" />
                      Success Story
                    </Badge>
                  </div>
                  {/* CHANGE: Replaced quotes with &quot; */}
                  <blockquote className="text-lg italic mb-4">&quot;{testimonial.quote}&quot;</blockquote>
                  <div>
                    <div className="font-semibold">{testimonial.author}</div>
                    <div className="text-sm text-muted-foreground">
                      {testimonial.role} at {testimonial.company}
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-3 gap-2 text-center">
                    {Object.entries(testimonial.metrics).map(([key, value]) => (
                      <div key={key} className="bg-gray-50 dark:bg-gray-800 rounded p-2">
                        <div className="font-semibold text-sm">{value}</div>
                        <div className="text-xs text-muted-foreground capitalize">{key}</div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="relative py-20 px-4 bg-gradient-to-r from-primary to-primary/90 text-primary-foreground overflow-hidden">
        {/* Background pattern */}
        <div className="absolute inset-0 opacity-10">
          <div className="absolute inset-0" style={{
            backgroundImage: `radial-gradient(circle at 2px 2px, currentColor 1px, transparent 1px)`,
            backgroundSize: '32px 32px'
          }} />
        </div>
        <div className="container mx-auto max-w-4xl text-center">
          <h2 className="text-4xl font-bold mb-4">Ready to Transform Your SEO?</h2>
          <p className="text-xl mb-8 opacity-90">
            Join thousands of companies using SerpTank to drive organic growth
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button size="lg" variant="secondary" onClick={() => router.push('/register')}>
              Start Free 14-Day Trial
              <ArrowRight className="ml-2 h-5 w-5" />
            </Button>
            <Button size="lg" variant="outline" onClick={() => router.push('/pricing')}>
              View Pricing Plans
            </Button>
          </div>
          <p className="mt-4 text-sm opacity-75">
            No credit card required • Full feature access • Cancel anytime
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 px-4 bg-gray-50 dark:bg-gray-900/50 border-t border-gray-200 dark:border-gray-800">
        <div className="container mx-auto max-w-7xl">
          <div className="grid md:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="flex items-center space-x-2 mb-4">
                <Zap className="h-6 w-6 text-primary" />
                <span className="text-xl font-bold">SerpTank</span>
              </div>
              <p className="text-sm text-muted-foreground">
                The enterprise SEO platform that delivers measurable business results.
              </p>
            </div>
            <div>
              <h3 className="font-semibold mb-4">Product</h3>
              <ul className="space-y-2 text-sm">
                <li><Link href="/features" className="hover:text-primary transition-colors">Features</Link></li>
                <li><Link href="/pricing" className="hover:text-primary transition-colors">Pricing</Link></li>
                <li><Link href="/case-studies" className="hover:text-primary transition-colors">Case Studies</Link></li>
                <li><Link href="/integrations" className="hover:text-primary transition-colors">Integrations</Link></li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold mb-4">Company</h3>
              <ul className="space-y-2 text-sm">
                <li><Link href="/about" className="hover:text-primary transition-colors">About</Link></li>
                <li><Link href="/blog" className="hover:text-primary transition-colors">Blog</Link></li>
                <li><Link href="/careers" className="hover:text-primary transition-colors">Careers</Link></li>
                <li><Link href="/contact" className="hover:text-primary transition-colors">Contact</Link></li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold mb-4">Resources</h3>
              <ul className="space-y-2 text-sm">
                <li><Link href="/docs" className="hover:text-primary transition-colors">Documentation</Link></li>
                <li><Link href="/api" className="hover:text-primary transition-colors">API Reference</Link></li>
                <li><Link href="/support" className="hover:text-primary transition-colors">Support</Link></li>
                <li><Link href="/status" className="hover:text-primary transition-colors">System Status</Link></li>
              </ul>
            </div>
          </div>
          <div className="border-t pt-8 flex flex-col md:flex-row justify-between items-center">
            <p className="text-sm text-muted-foreground">
              © 2024 SerpTank. All rights reserved.
            </p>
            <div className="flex space-x-4 mt-4 md:mt-0">
              <Link href="/privacy" className="text-sm hover:text-primary transition-colors">Privacy Policy</Link>
              <Link href="/terms" className="text-sm hover:text-primary transition-colors">Terms of Service</Link>
              <Link href="/security" className="text-sm hover:text-primary transition-colors">Security</Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}