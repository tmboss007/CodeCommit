import Link from 'next/link';
import { PageHeader } from '../components/ui/chrome';
import { Button } from '../components/ui/button';

export default function NotFound() {
  return (
    <div>
      <PageHeader title="Page not found" description="Use navigation to return to Command Center or Scenario Simulator." />
      <Link href="/"><Button>Command Center</Button></Link>
    </div>
  );
}
