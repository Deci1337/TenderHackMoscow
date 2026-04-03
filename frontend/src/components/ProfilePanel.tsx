import { useEffect, useState } from "react";
import { api, UserProfile } from "../api/client";
import { BarChart3, History, Tag } from "lucide-react";

interface Props {
  inn: string;
}

export default function ProfilePanel({ inn }: Props) {
  const [profile, setProfile] = useState<UserProfile | null>(null);

  useEffect(() => {
    api.getUser(inn).then(setProfile).catch(() => {});
  }, [inn]);

  if (!profile) return null;

  return (
    <aside className="bg-white rounded-xl border border-portal-border p-4 space-y-4">
      <div className="flex items-center gap-2">
        <BarChart3 size={16} className="text-portal-blue" />
        <span className="text-sm font-semibold">Ваш профиль</span>
      </div>

      {profile.industry && (
        <div className="flex items-center gap-2 text-sm text-portal-text-secondary">
          <Tag size={14} />
          <span>{profile.industry}</span>
        </div>
      )}

      <div className="flex items-center gap-2 text-sm text-portal-text-secondary">
        <History size={14} />
        <span>Контрактов в истории: <strong className="text-portal-text">{profile.total_contracts}</strong></span>
      </div>

      {profile.top_categories.length > 0 && (
        <div>
          <p className="text-xs text-portal-text-secondary mb-2 font-medium uppercase tracking-wide">
            Частые категории
          </p>
          <div className="flex flex-col gap-1">
            {profile.top_categories.map((cat, i) => (
              <span
                key={i}
                className="text-xs bg-portal-bg text-portal-text px-2 py-1 rounded truncate"
                title={cat}
              >
                {cat}
              </span>
            ))}
          </div>
        </div>
      )}
    </aside>
  );
}
