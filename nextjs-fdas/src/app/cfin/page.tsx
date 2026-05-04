import type { Metadata } from 'next';
import { redirect } from 'next/navigation';

export const metadata: Metadata = {
  title: 'Financial Document Analysis System | CFIN',
  description: 'Professional AI-powered financial document analysis and insights platform',
};

export default function CfinPage() {
  redirect('/product/cfin');
}
