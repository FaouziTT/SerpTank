'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { MagneticButton } from '@/components/ui/magnetic-button';
import { CTAButton } from '@/components/ui/cta-button';
import { SimpleMagneticWrapper } from '@/components/ui/simple-magnetic-wrapper';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { SEOOrb } from '@/components/ui/seo-orb';
import {
  ArrowRight,
  Book,
  BookOpen,
  ChevronRight,
  Clock,
  Code,
  Download,
  ExternalLink,
  FileText,
  Globe,
  Layers,
  LifeBuoy,
  Lightbulb,
  PlayCircle,
  Rocket,
  Search,
  Settings,
  Star,
  Users,
  Video,
  Zap,
} from 'lucide-react';
import { motion, useScroll, useTransform } from 'framer-motion';
import { useInView } from 'react-intersection-observer';

// Documentation categories
const docCategories = [
  {
    id: 'getting-started',
    title: 'Getting Started',
    icon: Rocket,
    description: 'Everything you need to know to get up and running quickly',
    color: 'from-blue-600 to-cyan-500',
    articles: [
      {
        title: 'Quick Start Guide',
        description: 'Get your first SEO project running in under 5 minutes',
        readTime: 5,
        difficulty: 'Beginner',
        popular: true,
      },
      {
        title: 'Account Setup & Configuration',
        description: 'Complete guide to setting up your SerpTank account',
        readTime: 8,
        difficulty: 'Beginner',
        popular: true,
      },
      {
        title: 'Understanding Your Dashboard',
        description: 'Navigate the SerpTank interface like a pro',
        readTime: 10,
        difficulty: 'Beginner',
        popular: false,
      },
      {
        title: 'First SEO Audit Walkthrough',
        description: 'Step-by-step guide to your first website audit',
        readTime: 15,
        difficulty: 'Beginner',
        popular: true,
      },
    ],
  },
  {
    id: 'features',
    title: 'Platform Features',
    icon: Layers,
    description: 'Deep dive into all SerpTank features and capabilities',
    color: 'from-purple-600 to-pink-500',
    articles: [
      {
        title: 'AI-Powered SEO Recommendations',
        description: 'How our AI analyzes and suggests improvements',
        readTime: 12,
        difficulty: 'Intermediate',
        popular: true,
      },
      {
        title: 'Keyword Research & Tracking',
        description: 'Find, analyze, and monitor your target keywords',
        readTime: 18,
        difficulty: 'Intermediate',
        popular: true,
      },
      {
        title: 'Competitor Analysis Tools',
        description: 'Analyze competition and find opportunities',
        readTime: 14,
        difficulty: 'Intermediate',
        popular: false,
      },
      {
        title: 'Content Optimization Workflows',
        description: 'Streamline your content creation and optimization',
        readTime: 16,
        difficulty: 'Advanced',
        popular: false,
      },
    ],
  },
  {
    id: 'integrations',
    title: 'Integrations',
    icon: Settings,
    description: 'Connect SerpTank with your existing tools and workflows',
    color: 'from-green-600 to-emerald-500',
    articles: [
      {
        title: 'Google Search Console Integration',
        description: 'Connect and sync your Search Console data',
        readTime: 8,
        difficulty: 'Beginner',
        popular: true,
      },
      {
        title: 'Google Analytics 4 Setup',
        description: 'Link GA4 for comprehensive traffic analysis',
        readTime: 10,
        difficulty: 'Intermediate',
        popular: true,
      },
      {
        title: 'WordPress Plugin Installation',
        description: 'Install and configure the SerpTank WordPress plugin',
        readTime: 6,
        difficulty: 'Beginner',
        popular: false,
      },
      {
        title: 'Third-Party Tool Connections',
        description: 'Connect with HubSpot, Shopify, and other platforms',
        readTime: 12,
        difficulty: 'Intermediate',
        popular: false,
      },
    ],
  },
  {
    id: 'api-developers',
    title: 'API & Developers',
    icon: Code,
    description: 'Technical documentation for developers and advanced users',
    color: 'from-orange-600 to-red-500',
    articles: [
      {
        title: 'API Authentication',
        description: 'Get started with SerpTank API authentication',
        readTime: 8,
        difficulty: 'Advanced',
        popular: true,
      },
      {
        title: 'REST API Reference',
        description: 'Complete API endpoints and usage examples',
        readTime: 25,
        difficulty: 'Advanced',
        popular: true,
      },
      {
        title: 'Webhook Configuration',
        description: 'Set up webhooks for real-time data updates',
        readTime: 12,
        difficulty: 'Advanced',
        popular: false,
      },
      {
        title: 'Custom Dashboard Development',
        description: 'Build custom dashboards using our API',
        readTime: 30,
        difficulty: 'Advanced',
        popular: false,
      },
    ],
  },
];

// Quick access resources
const quickAccess = [
  {
    title: 'Video Tutorials',
    description: '25+ step-by-step video guides',
    icon: Video,
    href: '/documentation/videos',
    color: 'text-blue-500',
  },
  {
    title: 'API Reference',
    description: 'Complete technical documentation',
    icon: Code,
    href: '/api',
    color: 'text-green-500',
  },
  {
    title: 'Support Center',
    description: 'Get help from our team',
    icon: LifeBuoy,
    href: '/support',
    color: 'text-purple-500',
  },
  {
    title: 'Community Forum',
    description: 'Connect with other users',
    icon: Users,
    href: 'https://community.serptank.com',
    color: 'text-orange-500',
  },
];

// Popular articles across all categories
const popularArticles = [
  {
    title: 'Quick Start Guide',
    category: 'Getting Started',
    readTime: 5,
    views: 45230,
    rating: 4.9,
  },
  {
    title: 'Google Search Console Integration',
    category: 'Integrations',
    readTime: 8,
    views: 38940,
    rating: 4.8,
  },
  {
    title: 'AI-Powered SEO Recommendations',
    category: 'Features',
    readTime: 12,
    views: 32180,
    rating: 4.9,
  },
  {
    title: 'API Authentication',
    category: 'API & Developers',
    readTime: 8,
    views: 28650,
    rating: 4.7,
  },
  {
    title: 'Keyword Research & Tracking',
    category: 'Features',
    readTime: 18,
    views: 25340,
    rating: 4.8,
  },
];

// Downloadable resources
const downloadableResources = [
  {
    title: 'SEO Checklist Template',
    description: 'Comprehensive checklist for SEO audits',
    format: 'PDF',
    size: '2.4 MB',
    downloads: 12400,
  },
  {
    title: 'Keyword Research Spreadsheet',
    description: 'Template for organizing keyword research',
    format: 'Excel',
    size: '1.8 MB',
    downloads: 8920,
  },
  {
    title: 'Content Calendar Template',
    description: 'Plan and organize your content strategy',
    format: 'Google Sheets',
    size: '1.2 MB',
    downloads: 15600,
  },
];

export default function DocumentationPage() {
  const router = useRouter();
  const [isScrolled, setIsScrolled] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
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

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    // In a real app, this would trigger a search
    console.log('Searching for:', searchQuery);
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
                {['Features', 'Pricing', 'Case Studies', 'About'].map((item) => (
                  <Link
                    key={item}
                    href={`/${item.toLowerCase().replace(' ', '-')}`}
                    className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors relative group"
                  >
                    {item}
                    <span className="absolute -bottom-1 left-0 w-0 h-0.5 bg-primary group-hover:w-full transition-all duration-300" />
                  </Link>
                ))}
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

      {/* Hero Section with Search */}
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
          <SEOOrb className="scale-150" colorTheme="blue" />
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
              <BookOpen className="mr-1 h-3 w-3" />
              Documentation
            </Badge>
          </motion.div>
          
          <motion.h1 
            className="text-5xl sm:text-6xl md:text-7xl lg:text-8xl font-bold tracking-tighter mb-8 leading-[0.9]"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.1 }}
          >
            <span className="block">Learn & Master</span>
            <span className="block text-gradient-electric mt-2">SerpTank</span>
          </motion.h1>
          
          <motion.p 
            className="text-lg sm:text-xl md:text-2xl text-muted-foreground mb-12 max-w-3xl mx-auto leading-relaxed"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
          >
            Comprehensive guides, tutorials, and resources to help you get the most
            out of your SEO platform and drive real business results.
          </motion.p>

          {/* Search Bar */}
          <motion.div 
            className="max-w-2xl mx-auto"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.3 }}
          >
            <form onSubmit={handleSearch} className="relative">
              <div className="relative">
                <Search className="absolute left-6 top-1/2 transform -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Search documentation, guides, and tutorials..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-14 pr-32 py-6 text-lg bg-card/80 backdrop-blur-sm border border-border/50 rounded-2xl focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/50 transition-all"
                />
                <CTAButton
                  type="submit"
                  size="sm"
                  className="absolute right-3 top-1/2 transform -translate-y-1/2"
                >
                  Search
                </CTAButton>
              </div>
            </form>
          </motion.div>
        </motion.div>
      </section>

      {/* Quick Access Resources */}
      <section className="relative section-padding">
        <div className="container-width px-6 mx-auto">
          <motion.div 
            className="text-center mb-12"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <h2 className="text-3xl font-bold mb-4">
              Quick <span className="text-gradient-neon">Access</span>
            </h2>
            <p className="text-muted-foreground text-lg">
              Jump to the most commonly accessed resources
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {quickAccess.map((resource, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 50 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6, delay: index * 0.1 }}
                whileHover={{ y: -10 }}
                className="group cursor-pointer"
                onClick={() => {
                  if (resource.href.startsWith('http')) {
                    window.open(resource.href, '_blank');
                  } else {
                    router.push(resource.href);
                  }
                }}
              >
                <Card className="text-center h-full bg-card/80 backdrop-blur-sm border-border/50 overflow-hidden card-float">
                  <div className="absolute inset-0 bg-gradient-to-br from-primary/[0.02] via-accent/[0.02] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                  <CardContent className="p-8 relative">
                    <resource.icon className={`h-12 w-12 mx-auto mb-4 ${resource.color} group-hover:scale-110 transition-transform duration-300`} />
                    <h3 className="font-semibold text-lg mb-2">{resource.title}</h3>
                    <p className="text-muted-foreground text-sm">{resource.description}</p>
                    {resource.href.startsWith('http') && (
                      <ExternalLink className="h-4 w-4 text-muted-foreground mt-3 mx-auto" />
                    )}
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Documentation Categories */}
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
              Browse by <span className="text-gradient">Category</span>
            </h2>
            <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
              Find exactly what you need with our organized documentation
            </p>
          </motion.div>

          <div className="space-y-16">
            {docCategories.map((category, categoryIndex) => (
              <motion.div
                key={category.id}
                initial={{ opacity: 0, y: 50 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6, delay: categoryIndex * 0.1 }}
              >
                {/* Category Header */}
                <div className="flex items-center space-x-4 mb-8">
                  <div className={`p-3 rounded-lg bg-gradient-to-br ${category.color}`}>
                    <category.icon className="h-6 w-6 text-white" />
                  </div>
                  <div>
                    <h3 className="text-2xl font-bold">{category.title}</h3>
                    <p className="text-muted-foreground">{category.description}</p>
                  </div>
                </div>

                {/* Category Articles */}
                <div className="grid md:grid-cols-2 lg:grid-cols-2 gap-6">
                  {category.articles.map((article, articleIndex) => (
                    <motion.div
                      key={articleIndex}
                      initial={{ opacity: 0, x: -20 }}
                      whileInView={{ opacity: 1, x: 0 }}
                      viewport={{ once: true }}
                      transition={{ duration: 0.5, delay: articleIndex * 0.1 }}
                      whileHover={{ x: 10 }}
                      className="group cursor-pointer"
                      onClick={() => router.push(`/documentation/${category.id}/${article.title.toLowerCase().replace(/\s+/g, '-')}`)}
                    >
                      <Card className="bg-card/80 backdrop-blur-sm border-border/50 hover:border-primary/50 transition-all duration-300">
                        <CardContent className="p-6">
                          <div className="flex items-start justify-between mb-4">
                            <div className="flex items-center space-x-3">
                              {article.popular && (
                                <Badge variant="secondary" className="bg-yellow-500/10 text-yellow-400 border-yellow-500/20">
                                  <Star className="h-3 w-3 mr-1" />
                                  Popular
                                </Badge>
                              )}
                              <Badge variant="outline" className="text-xs">
                                {article.difficulty}
                              </Badge>
                            </div>
                            <ChevronRight className="h-5 w-5 text-muted-foreground group-hover:text-primary transition-colors" />
                          </div>
                          <h4 className="font-semibold text-lg mb-2 group-hover:text-primary transition-colors">
                            {article.title}
                          </h4>
                          <p className="text-muted-foreground text-sm mb-4">
                            {article.description}
                          </p>
                          <div className="flex items-center text-xs text-muted-foreground">
                            <Clock className="h-3 w-3 mr-1" />
                            <span>{article.readTime} min read</span>
                          </div>
                        </CardContent>
                      </Card>
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Popular Articles & Resources */}
      <section className="relative section-padding">
        <div className="container-width px-6 mx-auto">
          <div className="grid lg:grid-cols-2 gap-16">
            {/* Popular Articles */}
            <motion.div
              initial={{ opacity: 0, x: -50 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
            >
              <div className="flex items-center space-x-3 mb-8">
                <Star className="h-6 w-6 text-yellow-500" />
                <h2 className="text-3xl font-bold">Most Popular Guides</h2>
              </div>
              
              <div className="space-y-4">
                {popularArticles.map((article, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, x: -20 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: index * 0.1 }}
                    whileHover={{ x: 10 }}
                    className="group cursor-pointer"
                    onClick={() => router.push(`/documentation/article/${article.title.toLowerCase().replace(/\s+/g, '-')}`)}
                  >
                    <Card className="bg-card/80 backdrop-blur-sm border-border/50 hover:border-primary/50 transition-all duration-300">
                      <CardContent className="p-6">
                        <div className="flex items-start justify-between">
                          <div className="space-y-2 flex-1">
                            <h3 className="font-semibold text-lg group-hover:text-primary transition-colors">
                              {article.title}
                            </h3>
                            <div className="flex items-center gap-4 text-sm text-muted-foreground">
                              <Badge variant="outline" className="text-xs">
                                {article.category}
                              </Badge>
                              <div className="flex items-center gap-1">
                                <Clock className="h-3 w-3" />
                                <span>{article.readTime} min</span>
                              </div>
                              <div className="flex items-center gap-1">
                                <Star className="h-3 w-3 fill-yellow-500 text-yellow-500" />
                                <span>{article.rating}</span>
                              </div>
                            </div>
                            <p className="text-xs text-muted-foreground">
                              {article.views.toLocaleString()} views
                            </p>
                          </div>
                          <ChevronRight className="h-5 w-5 text-muted-foreground group-hover:text-primary transition-colors flex-shrink-0 ml-4" />
                        </div>
                      </CardContent>
                    </Card>
                  </motion.div>
                ))}
              </div>
            </motion.div>

            {/* Downloadable Resources */}
            <motion.div
              initial={{ opacity: 0, x: 50 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
            >
              <div className="flex items-center space-x-3 mb-8">
                <Download className="h-6 w-6 text-primary" />
                <h2 className="text-3xl font-bold">Free Resources</h2>
              </div>
              
              <div className="space-y-4">
                {downloadableResources.map((resource, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, x: 20 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: index * 0.1 }}
                    whileHover={{ scale: 1.02 }}
                    className="group cursor-pointer"
                    onClick={() => console.log('Downloading:', resource.title)}
                  >
                    <Card className="bg-card/80 backdrop-blur-sm border-border/50 hover:border-primary/50 transition-all duration-300">
                      <CardContent className="p-6">
                        <div className="flex items-start space-x-4">
                          <div className="w-12 h-12 bg-gradient-to-br from-primary to-accent rounded-lg flex items-center justify-center flex-shrink-0">
                            <FileText className="h-6 w-6 text-white" />
                          </div>
                          <div className="space-y-2 flex-1">
                            <h3 className="font-semibold text-lg">{resource.title}</h3>
                            <p className="text-sm text-muted-foreground">{resource.description}</p>
                            <div className="flex items-center gap-4 text-xs text-muted-foreground">
                              <Badge variant="outline" className="text-xs">
                                {resource.format}
                              </Badge>
                              <span>{resource.size}</span>
                              <span>{resource.downloads.toLocaleString()} downloads</span>
                            </div>
                          </div>
                          <Download className="h-5 w-5 text-primary flex-shrink-0" />
                        </div>
                      </CardContent>
                    </Card>
                  </motion.div>
                ))}
              </div>

              {/* Additional Help */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.5 }}
                className="mt-8"
              >
                <Card className="bg-gradient-to-br from-primary/10 to-accent/10 border-primary/20">
                  <CardContent className="p-6 text-center">
                    <Lightbulb className="h-8 w-8 text-primary mx-auto mb-4" />
                    <h3 className="font-semibold text-lg mb-2">Need Help?</h3>
                    <p className="text-muted-foreground text-sm mb-4">
                      Can't find what you're looking for? Our support team is here to help.
                    </p>
                    <SimpleMagneticWrapper>
                      <CTAButton
                        size="sm"
                        onClick={() => router.push('/support')}
                      >
                        Contact Support
                      </CTAButton>
                    </SimpleMagneticWrapper>
                  </CardContent>
                </Card>
              </motion.div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="relative section-padding overflow-hidden">
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
            Ready to Get <span className="text-gradient-electric">Started</span>?
          </h2>
          <p className="text-xl text-muted-foreground mb-12 max-w-2xl mx-auto">
            Start your SEO journey with SerpTank and see the results for yourself
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
                onClick={() => router.push('/documentation/getting-started/quick-start-guide')}
                className="text-xl"
                magneticStrength={0}
              >
                Quick Start Guide
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
                        className={`transition-colors ${
                          link === 'Documentation' 
                            ? 'text-foreground font-medium' 
                            : 'text-muted-foreground hover:text-foreground'
                        }`}
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