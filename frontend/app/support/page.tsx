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
  BookOpen,
  CheckCircle2,
  Clock,
  Code,
  FileText,
  Globe,
  HelpCircle,
  LifeBuoy,
  Mail,
  MessageSquare,
  Phone,
  PlayCircle,
  Plus,
  Search,
  Star,
  Users,
  Video,
  Zap,
} from 'lucide-react';
import { motion, useScroll, useTransform } from 'framer-motion';
import { useInView } from 'react-intersection-observer';

// Support categories
const supportCategories = [
  {
    id: 'getting-started',
    title: 'Getting Started',
    icon: PlayCircle,
    description: 'New to SerpTank? Learn the basics and get up to speed quickly',
    articles: [
      'Setting up your first SEO project',
      'Understanding your SEO dashboard',
      'Connecting Google Search Console',
      'Adding team members and permissions',
      'Initial website audit walkthrough',
    ],
    color: 'from-blue-600 to-cyan-500',
  },
  {
    id: 'features-tutorials',
    title: 'Features & Tutorials',
    icon: BookOpen,
    description: 'In-depth guides for all platform features and capabilities',
    articles: [
      'Advanced keyword tracking setup',
      'Using AI-powered SEO recommendations',
      'Setting up automated reporting',
      'Competitor analysis best practices',
      'Content optimization workflows',
    ],
    color: 'from-green-600 to-emerald-500',
  },
  {
    id: 'api-developers',
    title: 'API & Developers',
    icon: Code,
    description: 'Technical documentation for developers and integrations',
    articles: [
      'API authentication and rate limits',
      'Webhook configuration guide',
      'Data export and import processes',
      'Custom dashboard development',
      'Third-party tool integrations',
    ],
    color: 'from-purple-600 to-pink-500',
  },
  {
    id: 'troubleshooting',
    title: 'Troubleshooting',
    icon: HelpCircle,
    description: 'Common issues and solutions to keep your SEO running smoothly',
    articles: [
      'Data not updating or syncing',
      'Login and authentication issues',
      'Report generation problems',
      'Performance and loading issues',
      'Integration connection failures',
    ],
    color: 'from-orange-600 to-red-500',
  },
];

// Popular help topics
const popularTopics = [
  {
    title: 'How to connect Google Search Console',
    category: 'Getting Started',
    views: 15420,
    helpful: 98,
  },
  {
    title: 'Understanding keyword difficulty scores',
    category: 'Features',
    views: 12380,
    helpful: 95,
  },
  {
    title: 'Setting up automated SEO reports',
    category: 'Features',
    views: 9870,
    helpful: 97,
  },
  {
    title: 'API rate limits and best practices',
    category: 'API',
    views: 8650,
    helpful: 92,
  },
  {
    title: 'Why is my data not updating?',
    category: 'Troubleshooting',
    views: 7420,
    helpful: 89,
  },
  {
    title: 'Team collaboration and permissions',
    category: 'Getting Started',
    views: 6890,
    helpful: 94,
  },
];

// Contact options
const contactOptions = [
  {
    title: 'Live Chat',
    description: 'Get instant help from our support team',
    availability: 'Available 24/7',
    responseTime: '< 5 minutes',
    icon: MessageSquare,
    color: 'from-blue-600 to-cyan-500',
    action: 'Start Chat',
    href: '#chat',
  },
  {
    title: 'Email Support',
    description: 'Detailed assistance for complex issues',
    availability: 'Monday - Friday',
    responseTime: '< 4 hours',
    icon: Mail,
    color: 'from-green-600 to-emerald-500',
    action: 'Send Email',
    href: 'mailto:support@serptank.com',
  },
  {
    title: 'Phone Support',
    description: 'Direct line for urgent technical issues',
    availability: 'Business Hours',
    responseTime: 'Immediate',
    icon: Phone,
    color: 'from-purple-600 to-pink-500',
    action: 'Call Now',
    href: 'tel:+1-555-123-4567',
  },
  {
    title: 'Community Forum',
    description: 'Connect with other users and experts',
    availability: 'Always Open',
    responseTime: 'Varies',
    icon: Users,
    color: 'from-orange-600 to-red-500',
    action: 'Join Discussion',
    href: 'https://community.serptank.com',
  },
];

// Video tutorials
const videoTutorials = [
  {
    title: 'SerpTank Platform Overview',
    description: 'Complete walkthrough of the SerpTank platform',
    duration: '12:30',
    thumbnail: '🎥',
    category: 'Getting Started',
  },
  {
    title: 'Advanced Keyword Research',
    description: 'Find and analyze the best keywords for your content',
    duration: '8:45',
    thumbnail: '🔍',
    category: 'Features',
  },
  {
    title: 'Setting Up Competitor Tracking',
    description: 'Monitor your competition and identify opportunities',
    duration: '6:20',
    thumbnail: '📊',
    category: 'Features',
  },
  {
    title: 'API Integration Basics',
    description: 'Getting started with the SerpTank API',
    duration: '15:10',
    thumbnail: '⚙️',
    category: 'API',
  },
];

// FAQ items
const faqItems = [
  {
    question: 'How long does it take to see SEO results?',
    answer: 'SEO results typically take 3-6 months to become visible, depending on your industry, competition, and the changes implemented. SerpTank provides early indicators and tracking to show progress before full results materialize.',
  },
  {
    question: 'Can I cancel my subscription anytime?',
    answer: 'Yes, you can cancel your subscription at any time. There are no long-term contracts or cancellation fees. Your account will remain active until the end of your current billing period.',
  },
  {
    question: 'Do you offer custom enterprise solutions?',
    answer: 'Yes, we provide custom enterprise solutions with dedicated support, custom integrations, white-label options, and enterprise-grade security features. Contact our sales team for more information.',
  },
  {
    question: 'How accurate is the SEO data?',
    answer: 'Our data is sourced directly from Google Search Console, Google Analytics, and other authoritative sources. We update most metrics daily and provide real-time tracking where possible.',
  },
  {
    question: 'Is there a mobile app available?',
    answer: 'Currently, SerpTank is optimized for web browsers and works excellently on mobile devices. A dedicated mobile app is in development and will be available in Q2 2025.',
  },
  {
    question: 'What integrations do you support?',
    answer: 'We integrate with Google Search Console, Google Analytics, Google Ads, Facebook Ads, WordPress, Shopify, HubSpot, and many other popular marketing tools. View our integrations page for the complete list.',
  },
];

export default function SupportPage() {
  const router = useRouter();
  const [isScrolled, setIsScrolled] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedFaq, setExpandedFaq] = useState<number | null>(null);
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

  const toggleFaq = (index: number) => {
    setExpandedFaq(expandedFaq === index ? null : index);
  };

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
      <section className="relative min-h-[70vh] flex items-center justify-center overflow-hidden pt-20">
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
          <SEOOrb className="scale-150" colorTheme="cyan" />
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
              <LifeBuoy className="mr-1 h-3 w-3" />
              Help & Support
            </Badge>
          </motion.div>
          
          <motion.h1 
            className="text-5xl sm:text-6xl md:text-7xl lg:text-8xl font-bold tracking-tighter mb-8 leading-[0.9]"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.1 }}
          >
            <span className="block">How Can We</span>
            <span className="block text-gradient-electric mt-2">Help You?</span>
          </motion.h1>
          
          <motion.p 
            className="text-lg sm:text-xl md:text-2xl text-muted-foreground mb-12 max-w-3xl mx-auto leading-relaxed"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
          >
            Find answers to your questions, learn how to use SerpTank effectively,
            and get the support you need to succeed with SEO.
          </motion.p>

          {/* Search Bar */}
          <motion.div 
            className="max-w-2xl mx-auto mb-12"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.3 }}
          >
            <form onSubmit={handleSearch} className="relative">
              <div className="relative">
                <Search className="absolute left-6 top-1/2 transform -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Search for help articles, tutorials, or guides..."
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

          <motion.div 
            className="flex items-center justify-center gap-8 text-sm text-muted-foreground"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.4 }}
          >
            <div className="flex items-center gap-2">
              <MessageSquare className="h-4 w-4 text-green-500" />
              <span>24/7 Live Chat</span>
            </div>
            <div className="flex items-center gap-2">
              <Mail className="h-4 w-4 text-blue-500" />
              <span>4hr Email Response</span>
            </div>
            <div className="flex items-center gap-2">
              <BookOpen className="h-4 w-4 text-purple-500" />
              <span>150+ Help Articles</span>
            </div>
          </motion.div>
        </motion.div>
      </section>

      {/* Section Divider */}
      <div className="w-full h-px bg-gradient-to-r from-transparent via-border/50 to-transparent" />
      
      {/* Support Categories */}
      <section className="relative section-padding bg-slate-50/30 dark:bg-slate-950/30 border-y border-border/30">
        <div className="absolute inset-0 bg-gradient-to-br from-slate-50/50 via-transparent to-slate-100/30 dark:from-slate-950/50 dark:via-transparent dark:to-slate-900/30" />
        <div className="container-width px-6 mx-auto relative z-10">
          <motion.div 
            className="text-center mb-16"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <h2 className="text-4xl sm:text-5xl font-bold mb-6">
              Browse by <span className="text-gradient-neon">Category</span>
            </h2>
            <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
              Find the help you need organized by topic and expertise level
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-16">
            {supportCategories.map((category, index) => (
              <motion.div
                key={category.id}
                initial={{ opacity: 0, y: 50 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6, delay: index * 0.1 }}
                whileHover={{ y: -10 }}
                className="group cursor-pointer"
                onClick={() => router.push(`/support/${category.id}`)}
              >
                <Card className="h-full bg-card/80 backdrop-blur-sm border-border/50 overflow-hidden card-float">
                  <div className="absolute inset-0 bg-gradient-to-br from-primary/[0.02] via-accent/[0.02] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                  <CardHeader className="relative">
                    <div className={`w-16 h-16 bg-gradient-to-br ${category.color} rounded-2xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300`}>
                      <category.icon className="h-8 w-8 text-white" />
                    </div>
                    <CardTitle className="text-xl">{category.title}</CardTitle>
                    <CardDescription className="text-base">
                      {category.description}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="relative">
                    <ul className="space-y-2">
                      {category.articles.slice(0, 3).map((article, idx) => (
                        <li key={idx} className="text-sm text-muted-foreground flex items-center">
                          <CheckCircle2 className="h-4 w-4 text-accent mr-2 flex-shrink-0" />
                          {article}
                        </li>
                      ))}
                      {category.articles.length > 3 && (
                        <li className="text-sm text-primary font-medium">
                          +{category.articles.length - 3} more articles
                        </li>
                      )}
                    </ul>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Section Divider */}
      <div className="w-full h-px bg-gradient-to-r from-transparent via-border/50 to-transparent" />
      
      {/* Contact Options */}
      <section className="relative section-padding bg-gradient-to-b from-background via-background/95 to-background border-y border-border/20">
        <div className="container-width px-6 mx-auto">
          <motion.div 
            className="text-center mb-16"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <h2 className="text-4xl sm:text-5xl font-bold mb-6">
              <span className="text-gradient">Get in Touch</span>
            </h2>
            <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
              Multiple ways to reach our support team for personalized assistance
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {contactOptions.map((option, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 50 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6, delay: index * 0.1 }}
                whileHover={{ y: -10 }}
                className="group"
              >
                <Card className="text-center h-full bg-card/80 backdrop-blur-sm border-border/50 overflow-hidden card-float">
                  <div className="absolute inset-0 bg-gradient-to-br from-primary/[0.02] via-accent/[0.02] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                  <CardHeader className="relative">
                    <div className={`w-16 h-16 bg-gradient-to-br ${option.color} rounded-2xl flex items-center justify-center mx-auto mb-4 group-hover:scale-110 transition-transform duration-300`}>
                      <option.icon className="h-8 w-8 text-white" />
                    </div>
                    <CardTitle className="text-xl">{option.title}</CardTitle>
                    <CardDescription className="text-base">
                      {option.description}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="relative space-y-4">
                    <div className="space-y-2">
                      <div className="flex items-center justify-center gap-2 text-sm">
                        <Clock className="h-4 w-4 text-accent" />
                        <span>{option.availability}</span>
                      </div>
                      <div className="text-sm text-muted-foreground">
                        Response: {option.responseTime}
                      </div>
                    </div>
                    <SimpleMagneticWrapper>
                      <CTAButton
                        size="sm"
                        onClick={() => {
                          if (option.href.startsWith('#')) {
                            // Handle internal actions like chat
                            console.log('Opening chat...');
                          } else {
                            window.open(option.href, '_blank');
                          }
                        }}
                        className="w-full"
                      >
                        {option.action}
                      </CTAButton>
                    </SimpleMagneticWrapper>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Section Divider */}
      <div className="w-full h-px bg-gradient-to-r from-transparent via-border/50 to-transparent" />
      
      {/* Popular Topics & Video Tutorials */}
      <section className="relative section-padding bg-gray-50/40 dark:bg-gray-950/40 border-y border-border/30">
        <div className="absolute inset-0 bg-gradient-to-r from-gray-50/60 via-gray-50/20 to-gray-100/40 dark:from-gray-950/60 dark:via-gray-950/20 dark:to-gray-900/40" />
        <div className="container-width px-6 mx-auto relative z-10">
          <div className="grid lg:grid-cols-2 gap-16">
            {/* Popular Topics */}
            <motion.div
              initial={{ opacity: 0, x: -50 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
            >
              <div className="flex items-center space-x-3 mb-8">
                <Star className="h-6 w-6 text-yellow-500" />
                <h2 className="text-3xl font-bold">Popular Help Topics</h2>
              </div>
              
              <div className="space-y-4">
                {popularTopics.map((topic, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, x: -20 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: index * 0.1 }}
                    whileHover={{ x: 10 }}
                    className="cursor-pointer"
                    onClick={() => router.push(`/support/article/${topic.title.toLowerCase().replace(/\s+/g, '-')}`)}
                  >
                    <Card className="bg-card/80 backdrop-blur-sm border-border/50 hover:border-primary/50 transition-all duration-300">
                      <CardContent className="p-6">
                        <div className="flex items-start justify-between">
                          <div className="space-y-2 flex-1">
                            <h3 className="font-semibold text-lg group-hover:text-primary transition-colors">
                              {topic.title}
                            </h3>
                            <div className="flex items-center gap-4 text-sm text-muted-foreground">
                              <Badge variant="outline" className="text-xs">
                                {topic.category}
                              </Badge>
                              <span>{topic.views.toLocaleString()} views</span>
                              <div className="flex items-center gap-1">
                                <CheckCircle2 className="h-3 w-3 text-green-500" />
                                <span>{topic.helpful}% helpful</span>
                              </div>
                            </div>
                          </div>
                          <ArrowRight className="h-5 w-5 text-muted-foreground group-hover:text-primary transition-colors flex-shrink-0 ml-4" />
                        </div>
                      </CardContent>
                    </Card>
                  </motion.div>
                ))}
              </div>
            </motion.div>

            {/* Video Tutorials */}
            <motion.div
              initial={{ opacity: 0, x: 50 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
            >
              <div className="flex items-center space-x-3 mb-8">
                <Video className="h-6 w-6 text-primary" />
                <h2 className="text-3xl font-bold">Video Tutorials</h2>
              </div>
              
              <div className="space-y-4">
                {videoTutorials.map((video, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, x: 20 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: index * 0.1 }}
                    whileHover={{ scale: 1.02 }}
                    className="cursor-pointer"
                    onClick={() => router.push(`/support/video/${video.title.toLowerCase().replace(/\s+/g, '-')}`)}
                  >
                    <Card className="bg-card/80 backdrop-blur-sm border-border/50 hover:border-primary/50 transition-all duration-300">
                      <CardContent className="p-6">
                        <div className="flex items-start space-x-4">
                          <div className="w-20 h-14 bg-gradient-to-br from-primary to-accent rounded-lg flex items-center justify-center text-2xl flex-shrink-0">
                            {video.thumbnail}
                          </div>
                          <div className="space-y-2 flex-1">
                            <h3 className="font-semibold text-lg">{video.title}</h3>
                            <p className="text-sm text-muted-foreground">{video.description}</p>
                            <div className="flex items-center gap-4 text-sm text-muted-foreground">
                              <Badge variant="outline" className="text-xs">
                                {video.category}
                              </Badge>
                              <div className="flex items-center gap-1">
                                <Clock className="h-3 w-3" />
                                <span>{video.duration}</span>
                              </div>
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Section Divider */}
      <div className="w-full h-px bg-gradient-to-r from-transparent via-border/50 to-transparent" />
      
      {/* FAQ Section */}
      <section className="relative section-padding bg-gradient-to-b from-background via-background/95 to-background border-y border-border/20">
        <div className="container-width px-6 mx-auto">
          <motion.div 
            className="text-center mb-16"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <h2 className="text-4xl sm:text-5xl font-bold mb-6">
              Frequently Asked <span className="text-gradient-electric">Questions</span>
            </h2>
            <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
              Quick answers to the most common questions about SerpTank
            </p>
          </motion.div>

          <div className="max-w-4xl mx-auto space-y-4">
            {faqItems.map((faq, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.05 }}
              >
                <Card className="bg-card/80 backdrop-blur-sm border-border/50 overflow-hidden">
                  <CardHeader 
                    className="cursor-pointer hover:bg-primary/5 transition-colors"
                    onClick={() => toggleFaq(index)}
                  >
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-lg pr-4">{faq.question}</CardTitle>
                      <motion.div
                        animate={{ rotate: expandedFaq === index ? 45 : 0 }}
                        transition={{ duration: 0.2 }}
                      >
                        <Plus className="h-5 w-5 text-muted-foreground flex-shrink-0" />
                      </motion.div>
                    </div>
                  </CardHeader>
                  <motion.div
                    initial={false}
                    animate={{ height: expandedFaq === index ? 'auto' : 0 }}
                    transition={{ duration: 0.3 }}
                    className="overflow-hidden"
                  >
                    <CardContent>
                      <p className="text-muted-foreground leading-relaxed">{faq.answer}</p>
                    </CardContent>
                  </motion.div>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Section Divider */}
      <div className="w-full h-px bg-gradient-to-r from-transparent via-border/50 to-transparent" />
      
      {/* CTA Section */}
      <section className="relative section-padding overflow-hidden bg-slate-50/20 dark:bg-slate-950/20 border-y border-border/30">
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
            Still Need <span className="text-gradient-electric">Help</span>?
          </h2>
          <p className="text-xl text-muted-foreground mb-12 max-w-2xl mx-auto">
            Our support team is standing by to help you succeed with SerpTank
          </p>
          <div className="flex flex-col sm:flex-row gap-6 justify-center">
            <SimpleMagneticWrapper>
              <CTAButton
                size="xl"
                onClick={() => console.log('Opening chat...')}
              >
                Start Live Chat
                <MessageSquare className="ml-2 h-5 w-5" />
              </CTAButton>
            </SimpleMagneticWrapper>
            <SimpleMagneticWrapper>
              <MagneticButton
                variant="glass"
                size="xl"
                onClick={() => window.open('mailto:support@serptank.com', '_blank')}
                className="text-xl"
                magneticStrength={0}
              >
                Email Support
              </MagneticButton>
            </SimpleMagneticWrapper>
          </div>
        </motion.div>
      </section>

      {/* Section Divider */}
      <div className="w-full h-px bg-gradient-to-r from-transparent via-border to-transparent" />
      
      {/* Modern Footer */}
      <footer className="relative py-16 bg-card/30 border-t border-border">
        <div className="absolute inset-0 bg-gradient-to-t from-card/50 to-transparent" />
        <div className="container-width px-6 mx-auto relative z-10">
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
                          link === 'Support' 
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