import { RefreshCw } from "lucide-react";

interface Props {
  reason: string;
}

export default function RankingChangeNotice({ reason }: Props) {
  return (
    <div className="flex items-start gap-2 bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 text-sm text-blue-800">
      <RefreshCw size={16} className="mt-0.5 shrink-0 text-blue-500" />
      <span>{reason}</span>
    </div>
  );
}
