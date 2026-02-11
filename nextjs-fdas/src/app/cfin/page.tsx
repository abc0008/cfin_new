import type { Metadata } from 'next';
import { CfinHeroPage } from '../page';

export const metadata: Metadata = {
  title: 'Financial Document Analysis System | CFIN',
  description: 'Professional AI-powered financial document analysis and insights platform',
};

export default function CfinPage() {
  return <CfinHeroPage />;
}
