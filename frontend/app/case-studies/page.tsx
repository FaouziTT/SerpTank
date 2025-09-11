'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { MagneticButton } from '@/components/ui/magnetic-button';
import { CTAButton } from '@/components/ui/cta-button';
import { SimpleMagneticWrapper } from '@/components/ui/simple-magnetic-wrapper';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { SEOOrb } from '@/components/ui/seo-orb';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  ArrowRight,
  ArrowUpRight,
  Award,
  BarChart3,
  BookOpen,
  Building2,
  Calendar,
  ChartBar,
  CheckCircle,
  CheckCircle2,
  Clock,
  DollarSign,
  Download,
  Eye,
  FileText,
  Filter,
  Globe,
  Lightbulb,
  LineChart,
  MapPin,
  Megaphone,
  MousePointer,
  Package,
  Percent,
  PieChart,
  Play,
  Quote,
  Rocket,
  Search,
  ShoppingBag,
  ShoppingCart,
  Sparkles,
  Star,
  Target,
  TrendingUp,
  Trophy,
  Users,
  Zap,
  AlertCircle,
  ChevronRight,
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

// Case study categories with gradients
const categories = [
  { id: 'all', name: 'All Industries', count: 12, gradient: 'from-blue-600 to-cyan-500' },
  { id: 'ecommerce', name: 'E-commerce', count: 4, gradient: 'from-purple-600 to-pink-500' },
  { id: 'saas', name: 'SaaS', count: 3, gradient: 'from-green-600 to-emerald-500' },
  { id: 'finance', name: 'Finance', count: 2, gradient: 'from-orange-600 to-amber-500' },
  { id: 'healthcare', name: 'Healthcare', count: 2, gradient: 'from-red-600 to-rose-500' },
  { id: 'media', name: 'Media', count: 1, gradient: 'from-indigo-600 to-violet-500' },
];

// Detailed case studies with enhanced data
const caseStudies = [
  {
    id: 'techcorp-global',
    category: 'saas',
    gradient: 'from-green-600 to-emerald-500',
    company: 'TechCorp Global',
    logo: '🏢',
    industry: 'SaaS / Technology',
    size: '500-1000 employees',
    location: 'San Francisco, CA',
    title: 'How TechCorp Achieved 400% Organic Traffic Growth in 6 Months',
    summary: 'Enterprise SaaS company transforms their SEO strategy with AI-powered insights and comprehensive diagnostics.',
    image: '/api/placeholder/600/400',
    results: {
      traffic: { value: '+400%', label: 'Organic Traffic', icon: TrendingUp },
      revenue: { value: '+$2.3M', label: 'Annual Revenue', icon: DollarSign },
      rankings: { value: '156', label: '#1 Rankings', icon: Trophy },
      roi: { value: '823%', label: 'ROI', icon: Target },
    },
    challenges: [
      'Low organic visibility in competitive market',
      'Technical SEO issues affecting 60% of pages',
      'No clear content strategy or keyword targeting',
      'Unable to measure SEO impact on revenue',
    ],
    solutions: [
      'Implemented comprehensive technical SEO audit and fixes',
      'Developed AI-driven content strategy targeting high-value keywords',
      'Created topic clusters for thought leadership',
      'Set up advanced revenue attribution tracking',
    ],
    quote: {
      text: "SerpTank transformed our SEO from a cost center to a revenue driver. The AI insights helped us identify opportunities we never knew existed.",
      author: 'Sarah Chen',
      role: 'VP of Marketing',
    },
    timeline: '6 months',
    tools: ['SEO Diagnostics', 'AI Market Simulation', 'Content Workflow', 'Profitability Tracking'],
  },
  {
    id: 'ecommerce-giants',
    category: 'ecommerce',
    gradient: 'from-purple-600 to-pink-500',
    company: 'E-commerce Giants',
    logo: '🛍️',
    industry: 'E-commerce / Retail',
    size: '1000+ employees',
    location: 'New York, NY',
    title: 'E-commerce Giant Dominates Search with 89% First-Page Rankings',
    summary: 'Major online retailer leverages SerpTank to outrank competitors and boost conversions.',
    image: '/api/placeholder/600/400',
    results: {
      rankings: { value: '89%', label: 'First Page', icon: Trophy },
      conversion: { value: '+67%', label: 'Conversion Rate', icon: ShoppingCart },
      revenue: { value: '+$5.1M', label: 'SEO Revenue', icon: DollarSign },
      speed: { value: '-2.3s', label: 'Load Time', icon: Zap },
    },
    challenges: [
      'Losing market share to aggressive competitors',
      'Poor site performance affecting rankings',
      'Inefficient product page optimization',
      'Difficulty scaling SEO across 100k+ products',
    ],
    solutions: [
      'Automated product page optimization at scale',
      'Implemented Core Web Vitals improvements',
      'Dynamic meta generation using AI',
      'Competitive gap analysis and targeting',
    ],
    quote: {
      text: "The ability to optimize 100,000+ product pages automatically was a game-changer. We saw results within weeks.",
      author: 'Michael Rodriguez',
      role: 'Head of Digital',
    },
    timeline: '4 months',
    tools: ['SEO Diagnostics', 'Competitive Analysis', 'SGE Readiness', 'Performance Monitoring'],
  },
  {
    id: 'finance-leaders',
    category: 'finance',
    gradient: 'from-orange-600 to-amber-500',
    company: 'Finance Leaders Inc',
    logo: '💼',
    industry: 'Financial Services',
    size: '200-500 employees',
    location: 'Chicago, IL',
    title: 'Financial Services Firm Achieves 312% ROI with Strategic SEO',
    summary: 'How a finance company turned SEO into their most profitable marketing channel.',
    image: '/api/placeholder/600/400',
    results: {
      roi: { value: '312%', label: 'Return on Investment', icon: Target },
      leads: { value: '+450%', label: 'Qualified Leads', icon: Users },
      cost: { value: '-45%', label: 'Cost per Lead', icon: DollarSign },
      authority: { value: '+82', label: 'Domain Authority', icon: Award },
    },
    challenges: [
      'Highly regulated industry with content restrictions',
      'Difficulty proving SEO value to executives',
      'Low E-E-A-T signals affecting rankings',
      'Minimal organic lead generation',
    ],
    solutions: [
      'Built comprehensive E-E-A-T optimization strategy',
      'Created ROI dashboard for C-suite reporting',
      'Developed compliant content workflows',
      'Implemented advanced lead tracking',
    ],
    quote: {
      text: "The ROI tracking features finally allowed us to show the CFO exactly how SEO impacts our bottom line.",
      author: 'Jennifer Park',
      role: 'CMO',
    },
    timeline: '3 months',
    tools: ['Profitability Analysis', 'Knowledge Engine', 'Content Workflow', 'Executive Dashboards'],
  },
  {
    id: 'healthcare-innovators',
    category: 'healthcare',
    gradient: 'from-red-600 to-rose-500',
    company: 'HealthTech Innovators',
    logo: '🏥',
    industry: 'Healthcare Technology',
    size: '100-200 employees',
    location: 'Boston, MA',
    title: 'HealthTech Startup Grows 10x with Content-Led SEO Strategy',
    summary: 'B2B healthcare platform builds authority and drives growth through strategic SEO.',
    image: '/api/placeholder/600/400',
    results: {
      traffic: { value: '10x', label: 'Organic Growth', icon: Rocket },
      authority: { value: '+45', label: 'Domain Rating', icon: Award },
      content: { value: '500+', label: 'Pages Created', icon: FileText },
      demos: { value: '+380%', label: 'Demo Requests', icon: Calendar },
    },
    challenges: [
      'Zero organic presence in competitive market',
      'Complex medical topics difficult to rank for',
      'Limited content resources and expertise',
      'Needed to build trust in healthcare space',
    ],
    solutions: [
      'AI-assisted medical content creation',
      'Built topical authority with cluster strategy',
      'Optimized for healthcare-specific schemas',
      'Created expert author profiles for E-E-A-T',
    ],
    quote: {
      text: "SerpTank&apos;s AI helped us create medically accurate content at scale while maintaining quality and compliance.",
      author: 'Dr. Robert Kim',
      role: 'VP of Growth',
    },
    timeline: '8 months',
    tools: ['Knowledge Engine', 'AI Content Assistant', 'Topic Clustering', 'Schema Optimization'],
  },
  {
    id: 'media-publishers',
    category: 'media',
    gradient: 'from-indigo-600 to-violet-500',
    company: 'Digital Media Publishers',
    logo: '📰',
    industry: 'Media & Publishing',
    size: '50-100 employees',
    location: 'Los Angeles, CA',
    title: 'Publisher Increases Ad Revenue 250% with SEO Optimization',
    summary: 'Digital publisher leverages SEO to drive traffic and maximize ad revenue.',
    image: '/api/placeholder/600/400',
    results: {
      traffic: { value: '+180%', label: 'Page Views', icon: Eye },
      revenue: { value: '+250%', label: 'Ad Revenue', icon: DollarSign },
      speed: { value: '95', label: 'PageSpeed Score', icon: Zap },
      serp: { value: '73%', label: 'Featured Snippets', icon: Star },
    },
    challenges: [
      'Declining organic traffic due to algorithm updates',
      'Poor site performance affecting user experience',
      'Difficulty optimizing for featured snippets',
      'Need to increase pages per session',
    ],
    solutions: [
      'Complete Core Web Vitals optimization',
      'SGE and featured snippet optimization',
      'Internal linking strategy for engagement',
      'Real-time content optimization',
    ],
    quote: {
      text: "The SGE readiness features positioned us perfectly for the future of search. We&apos;re ahead of the curve.",
      author: 'Maria Santos',
      role: 'Director of SEO',
    },
    timeline: '5 months',
    tools: ['SGE Readiness', 'Performance Monitoring', 'Content Optimization', 'Real-time Analytics'],
  },
  {
    id: 'local-retail-chain',
    category: 'ecommerce',
    gradient: 'from-purple-600 to-pink-500',
    company: 'Regional Retail Chain',
    logo: '🏪',
    industry: 'Retail',
    size: '1000+ employees',
    location: 'Dallas, TX',
    title: 'Retail Chain Drives 45% More Foot Traffic with Local SEO',
    summary: 'Multi-location retailer dominates local search and drives in-store visits.',
    image: '/api/placeholder/600/400',
    results: {
      traffic: { value: '+45%', label: 'Store Visits', icon: MapPin },
      local: { value: '95%', label: 'Local Pack Rankings', icon: Trophy },
      reviews: { value: '+1,200', label: 'New Reviews', icon: Star },
      sales: { value: '+$3.8M', label: 'In-Store Revenue', icon: DollarSign },
    },
    challenges: [
      'Inconsistent local listings across 150 locations',
      'Poor local search visibility',
      'Minimal customer reviews',
      'Difficulty tracking online-to-offline conversions',
    ],
    solutions: [
      'Automated local listing management',
      'Location-specific landing page optimization',
      'Review generation and management system',
      'Advanced foot traffic attribution',
    ],
    quote: {
      text: "We finally connected our SEO efforts directly to in-store sales. The ROI is undeniable.",
      author: 'James Wilson',
      role: 'VP of Digital Marketing',
    },
    timeline: '6 months',
    tools: ['Local SEO Suite', 'Review Management', 'Conversion Tracking', 'Multi-location Dashboard'],
  },
];

// Success metrics with animations
const AnimatedMetric = ({ value, suffix = '' }: { value: number; suffix?: string }) => {
  const [count, setCount] = useState(0);
  const [ref, inView] = useInView({ triggerOnce: true });

  useEffect(() => {
    if (inView) {
      const timer = setInterval(() => {
        setCount(prev => {
          if (prev < value) {
            return Math.min(prev + Math.ceil(value / 50), value);
          }
          return value;
        });
      }, 30);
      return () => clearInterval(timer);
    }
  }, [inView, value]);

  return (
    <span ref={ref} className="tabular-nums">
      {count}{suffix}
    </span>
  );
};

const aggregateMetrics = [
  { label: 'Average Traffic Increase', value: 287, suffix: '%', icon: TrendingUp, gradient: 'from-blue-600 to-cyan-500' },
  { label: 'Average ROI', value: 415, suffix: '%', icon: DollarSign, gradient: 'from-green-600 to-emerald-500' },
  { label: 'Total Revenue Generated', prefix: '$', value: 23.5, suffix: 'M', icon: Trophy, gradient: 'from-purple-600 to-pink-500' },
  { label: 'Keywords Ranking #1', value: 3456, suffix: '', icon: Target, gradient: 'from-orange-600 to-amber-500' },
];

// Case study card component
const CaseStudyCard = ({ study, index, isExpanded, onToggle }: any) => {
  const [ref, inView] = useInView({ triggerOnce: true, threshold: 0.1 });
  const router = useRouter();
  
  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 50 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.6, delay: index * 0.1 }}
      className="group"
    >
      <Card className="overflow-hidden bg-card/80 backdrop-blur-sm border-border/50 hover:border-primary/50 transition-all duration-300">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/[0.02] via-accent/[0.02] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
        
        <div className="relative grid md:grid-cols-3 gap-6 p-6 md:p-8">
          {/* Company Info */}
          <div className="md:col-span-1">
            <div className="flex items-start space-x-4 mb-6">
              <div className={`w-16 h-16 rounded-2xl bg-gradient-to-br ${study.gradient} flex items-center justify-center text-3xl shadow-lg`}>
                {study.logo}
              </div>
              <div>
                <h3 className="font-bold text-xl">{study.company}</h3>
                <p className="text-sm text-muted-foreground">{study.industry}</p>
              </div>
            </div>
            <div className="space-y-3 text-sm">
              <div className="flex items-center text-muted-foreground">
                <Users className="h-4 w-4 mr-3 text-accent" />
                {study.size}
              </div>
              <div className="flex items-center text-muted-foreground">
                <MapPin className="h-4 w-4 mr-3 text-accent" />
                {study.location}
              </div>
              <div className="flex items-center text-muted-foreground">
                <Clock className="h-4 w-4 mr-3 text-accent" />
                {study.timeline} implementation
              </div>
            </div>
          </div>

          {/* Results & Details */}
          <div className="md:col-span-2">
            <h2 className="text-2xl md:text-3xl font-bold mb-3">{study.title}</h2>
            <p className="text-muted-foreground mb-6 text-lg">{study.summary}</p>

            {/* Key Results Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              {/* CHANGE: Added type annotation to fix 'unknown' type error */}
              {Object.entries(study.results).map(([key, result]: [string, any]) => (
                <motion.div 
                  key={key} 
                  className="text-center p-4 bg-gradient-to-br from-card to-card/50 border border-border/50 rounded-xl hover:border-primary/50 transition-all duration-300"
                  whileHover={{ y: -5 }}
                >
                  <result.icon className="h-6 w-6 text-primary mx-auto mb-2" />
                  <div className="text-2xl font-bold text-gradient">{result.value}</div>
                  <div className="text-xs text-muted-foreground">{result.label}</div>
                </motion.div>
              ))}
            </div>

            {/* Quote */}
            <Card className="mb-8 bg-gradient-to-br from-primary/5 to-accent/5 border-primary/20 overflow-hidden">
              <CardContent className="p-6 relative">
                <Quote className="h-8 w-8 text-primary/20 absolute top-4 left-4" />
                <blockquote className="italic text-lg mb-3 pl-12">{study.quote.text}</blockquote>
                <div className="text-sm pl-12">
                  <span className="font-semibold">{study.quote.author}</span>
                  <span className="text-muted-foreground"> • {study.quote.role}</span>
                </div>
              </CardContent>
            </Card>

            {/* Expand Button */}
            <SimpleMagneticWrapper>
              <MagneticButton
                variant="secondary"
                onClick={onToggle}
                magneticStrength={0}
              >
                {isExpanded ? 'Show Less' : 'View Full Case Study'}
                <ChevronRight className={`ml-2 h-4 w-4 transition-transform ${
                  isExpanded ? 'rotate-90' : ''
                }`} />
              </MagneticButton>
            </SimpleMagneticWrapper>

            {/* Expanded Details */}
            <motion.div
              initial={false}
              animate={{ height: isExpanded ? 'auto' : 0 }}
              transition={{ duration: 0.3 }}
              className="overflow-hidden"
            >
              <div className="mt-8 space-y-8">
                <div>
                  <h4 className="font-semibold text-lg mb-4 flex items-center">
                    <AlertCircle className="h-5 w-5 mr-2 text-destructive" />
                    Challenges
                  </h4>
                  <ul className="space-y-3">
                    {study.challenges.map((challenge: string, idx: number) => (
                      <motion.li 
                        key={idx} 
                        className="flex items-start"
                        initial={{ opacity: 0, x: -20 }}
                        animate={isExpanded ? { opacity: 1, x: 0 } : {}}
                        transition={{ delay: idx * 0.05 }}
                      >
                        <CheckCircle2 className="h-5 w-5 text-destructive mr-3 mt-0.5 flex-shrink-0" />
                        <span>{challenge}</span>
                      </motion.li>
                    ))}
                  </ul>
                </div>

                <div>
                  <h4 className="font-semibold text-lg mb-4 flex items-center">
                    <Lightbulb className="h-5 w-5 mr-2 text-accent" />
                    Solutions
                  </h4>
                  <ul className="space-y-3">
                    {study.solutions.map((solution: string, idx: number) => (
                      <motion.li 
                        key={idx} 
                        className="flex items-start"
                        initial={{ opacity: 0, x: -20 }}
                        animate={isExpanded ? { opacity: 1, x: 0 } : {}}
                        transition={{ delay: idx * 0.05 }}
                      >
                        <CheckCircle2 className="h-5 w-5 text-accent mr-3 mt-0.5 flex-shrink-0" />
                        <span>{solution}</span>
                      </motion.li>
                    ))}
                  </ul>
                </div>

                <div>
                  <h4 className="font-semibold text-lg mb-4 flex items-center">
                    <Zap className="h-5 w-5 mr-2 text-primary" />
                    SerpTank Tools Used
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {study.tools.map((tool: string, idx: number) => (
                      <Badge key={idx} className="px-4 py-1.5 bg-gradient-to-r from-primary/10 to-accent/10 border-primary/20">
                        {tool}
                      </Badge>
                    ))}
                  </div>
                </div>

                <div className="flex flex-col sm:flex-row gap-4 pt-4">
                  <SimpleMagneticWrapper>
                    <CTAButton
                      size="lg"
                      onClick={() => router.push('/register')}
                    >
                      Get Similar Results
                      <ArrowRight className="ml-2 h-5 w-5" />
                    </CTAButton>
                  </SimpleMagneticWrapper>
                  <SimpleMagneticWrapper>
                    <MagneticButton
                      variant="glass"
                      size="lg"
                      magneticStrength={0}
                    >
                      <Download className="mr-2 h-5 w-5" />
                      Download PDF
                    </MagneticButton>
                  </SimpleMagneticWrapper>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </Card>
    </motion.div>
  );
};

export default function CaseStudiesPage() {
  const router = useRouter();
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [expandedStudy, setExpandedStudy] = useState<string | null>(null);
  const [isScrolled, setIsScrolled] = useState(false);
  const { scrollY } = useScroll();
  
  // Parallax transforms
  const heroY = useTransform(scrollY, [0, 500], [0, 150]);
  const orbScale = useTransform(scrollY, [0, 500], [1, 0.8]);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 10);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const filteredStudies = selectedCategory === 'all'
    ? caseStudies
    : caseStudies.filter(study => study.category === selectedCategory);

  const toggleStudy = (studyId: string) => {
    setExpandedStudy(expandedStudy === studyId ? null : studyId);
  };

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
                  className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors relative group"
                >
                  Features
                  <span className="absolute -bottom-1 left-0 w-0 h-0.5 bg-primary group-hover:w-full transition-all duration-300" />
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
                  className="text-sm font-medium text-foreground relative group"
                >
                  Case Studies
                  <span className="absolute -bottom-1 left-0 w-full h-0.5 bg-primary" />
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
        <div className="absolute inset-0 gradient-mesh opacity-20 dark:opacity-10" />
        
        {/* Enhanced floating 3D orb */}
        <motion.div
          className="absolute right-[-200px] top-1/2 -translate-y-1/2 w-[800px] h-[800px] lg:w-[1000px] lg:h-[1000px]"
          style={{ y: heroY, scale: orbScale }}
        >
          <SEOOrb className="scale-150" colorTheme="orange" />
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
              <Trophy className="mr-1 h-3 w-3" />
              Customer Success Stories
            </Badge>
          </motion.div>
          
          <motion.h1 
            className="text-5xl sm:text-6xl md:text-7xl lg:text-8xl font-bold tracking-tighter mb-8 leading-[0.9]"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.1 }}
          >
            <span className="block">Real Results from</span>
            <span className="block text-gradient-electric mt-2">Real Businesses</span>
          </motion.h1>
          
          <motion.p 
            className="text-lg sm:text-xl md:text-2xl text-muted-foreground mb-12 max-w-3xl mx-auto leading-relaxed"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
          >
            Discover how leading companies use SerpTank to transform their SEO strategy,
            drive organic growth, and achieve measurable business results.
          </motion.p>
        </motion.div>
      </section>

      {/* Aggregate Metrics with Animated Counters */}
      <section className="relative section-padding bg-gradient-to-b from-background via-background/95 to-background">
        <div className="container-width px-6 mx-auto">
          <div className="grid md:grid-cols-4 gap-6">
            {aggregateMetrics.map((metric, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 50 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6, delay: index * 0.1 }}
                whileHover={{ y: -5 }}
                className="group"
              >
                <Card className="relative overflow-hidden bg-card/80 backdrop-blur-sm border-border/50 hover:border-primary/50 transition-all duration-300">
                  <div className="absolute inset-0 bg-gradient-to-br from-primary/[0.02] via-accent/[0.02] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                  
                  <CardContent className="p-6 relative">
                    <div className="flex items-center justify-between mb-4">
                      <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${metric.gradient} flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform duration-300`}>
                        <metric.icon className="h-6 w-6 text-white" />
                      </div>
                      <Badge variant="secondary" className="bg-gradient-to-r from-primary/10 to-accent/10 border-primary/20">
                        Avg
                      </Badge>
                    </div>
                    <div className="text-4xl font-bold mb-2 text-gradient">
                      {metric.prefix}<AnimatedMetric value={metric.value} suffix={metric.suffix} />
                    </div>
                    <div className="text-sm text-muted-foreground">{metric.label}</div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Category Filter with Glass Effect */}
      <section className="sticky top-20 z-40 py-6 bg-background/80 backdrop-blur-xl border-b border-border">
        <div className="container-width px-6 mx-auto">
          <div className="flex items-center space-x-4 overflow-x-auto pb-2 scrollbar-hide">
            <Filter className="h-5 w-5 text-muted-foreground flex-shrink-0" />
            {categories.map((category) => (
              <SimpleMagneticWrapper key={category.id}>
                <button
                  onClick={() => setSelectedCategory(category.id)}
                  className={`flex items-center space-x-2 px-6 py-3 rounded-xl whitespace-nowrap transition-all duration-300 ${
                    selectedCategory === category.id
                      ? 'bg-gradient-to-r ' + category.gradient + ' text-white shadow-lg shadow-primary/25'
                      : 'bg-card/50 backdrop-blur-sm border border-border/50 hover:bg-card/80 hover:border-primary/50'
                  }`}
                >
                  <span className="font-semibold">{category.name}</span>
                  <Badge className={`${
                    selectedCategory === category.id 
                      ? 'bg-white/20 text-white border-white/30' 
                      : 'bg-primary/10 border-primary/20'
                  }`}>
                    {category.count}
                  </Badge>
                </button>
              </SimpleMagneticWrapper>
            ))}
          </div>
        </div>
      </section>

      {/* Case Studies Grid */}
      <section className="relative section-padding">
        <div className="container-width px-6 mx-auto">
          <div className="grid gap-8">
            {filteredStudies.map((study, index) => (
              <CaseStudyCard
                key={study.id}
                study={study}
                index={index}
                isExpanded={expandedStudy === study.id}
                onToggle={() => toggleStudy(study.id)}
              />
            ))}
          </div>
        </div>
      </section>

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
            Ready to Write Your <span className="text-gradient-neon">Success Story</span>?
          </h2>
          <p className="text-xl text-muted-foreground mb-12 max-w-2xl mx-auto">
            Join thousands of companies achieving remarkable results with SerpTank
          </p>
          <div className="flex flex-col sm:flex-row gap-6 justify-center">
            <SimpleMagneticWrapper>
              <CTAButton
                size="xl"
                onClick={() => router.push('/register')}
              >
                Start Your Free Trial
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
                Request a Demo
              </MagneticButton>
            </SimpleMagneticWrapper>
          </div>
        </motion.div>
      </section>

      {/* Modern Footer */}
      <footer className="relative py-16 border-t border-border">
        <div className="container-width px-6 mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-8 lg:gap-12 mb-12">
            <div className="col-span-2">
              <div className="flex items-center space-x-3 mb-6">
                <div className="relative w-8 h-8">
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