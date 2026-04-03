import { useCallback, useState } from "react";
import { api } from "./api/client";
import DemoSwitcher from "./components/DemoSwitcher";
import Header from "./components/Header";
import OnboardingModal from "./components/OnboardingModal";
import Pagination from "./components/Pagination";
import ProfilePanel from "./components/ProfilePanel";
import RankingChangeNotice from "./components/RankingChangeNotice";
import SearchBar from "./components/SearchBar";
import STECard from "./components/STECard";
import { useEvents } from "./hooks/useEvents";
import { useSearch } from "./hooks/useSearch";
import { PackageSearch } from "lucide-react";

const PAGE_SIZE = 20;

interface CurrentUser {
  inn: string;
  name: string | null;
  industry: string | null;
}

function generateSessionId() {
  return `s_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

export default function App() {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [sessionId] = useState(generateSessionId);
  const [lastQuery, setLastQuery] = useState("");
  const [offset, setOffset] = useState(0);

  const { response, loading, search } = useSearch(user?.inn || "", sessionId);
  const { trackClick, trackBounce, track } = useEvents(user?.inn || "", sessionId);

  const handleOnboard = useCallback(
    async (inn: string, name: string, industry: string) => {
      try {
        await api.onboard(inn, name, undefined, industry);
      } catch {
        // API may not be running during local development
      }
      setUser({ inn, name, industry });
    },
    []
  );

  const handleSearch = useCallback(
    (query: string, newOffset = 0) => {
      setLastQuery(query);
      setOffset(newOffset);
      search(query, newOffset, PAGE_SIZE);
    },
    [search]
  );

  const handlePageChange = useCallback(
    (newOffset: number) => {
      handleSearch(lastQuery, newOffset);
      window.scrollTo({ top: 0, behavior: "smooth" });
    },
    [handleSearch, lastQuery]
  );

  const handleAction = useCallback(
    (steId: number, action: string) => {
      if (action === "click") {
        trackClick(steId, lastQuery);
        setTimeout(() => trackBounce(steId, lastQuery), 2500);
      } else {
        track(steId, action, lastQuery);
      }
    },
    [track, trackClick, trackBounce, lastQuery]
  );

  if (!user) {
    return <OnboardingModal onComplete={handleOnboard} />;
  }

  return (
    <div className="min-h-screen bg-portal-bg">
      <Header currentUser={user} onSwitchUser={() => setUser(null)} />

      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="text-center mb-8">
          <h2 className="text-2xl font-bold text-portal-text mb-2">Поиск по каталогу СТЕ</h2>
          <p className="text-portal-text-secondary text-sm">
            Персонализированный поиск с учётом вашей истории закупок
          </p>
        </div>

        <SearchBar
          onSearch={(q) => handleSearch(q, 0)}
          loading={loading}
          correctedQuery={response?.corrected_query || null}
          didYouMean={null}
        />

        <div className="mt-8 flex gap-6 items-start">
          {/* Sidebar */}
          <aside className="hidden lg:block w-64 shrink-0 space-y-4">
            <ProfilePanel inn={user.inn} />
          </aside>

          {/* Results */}
          <div className="flex-1 min-w-0">
            {response?.did_you_mean && (
              <div className="mb-4">
                <RankingChangeNotice reason={response.did_you_mean} />
              </div>
            )}

            {response && (
              <>
                <p className="text-sm text-portal-text-secondary mb-4">
                  Найдено:{" "}
                  <span className="font-semibold text-portal-text">{response.total}</span>{" "}
                  результатов по запросу «{response.query}»
                </p>

                {response.results.length > 0 ? (
                  <>
                    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                      {response.results.map((item) => (
                        <STECard
                          key={item.id}
                          item={item}
                          query={lastQuery}
                          onAction={handleAction}
                        />
                      ))}
                    </div>
                    <Pagination
                      total={response.total}
                      limit={PAGE_SIZE}
                      offset={offset}
                      onPageChange={handlePageChange}
                    />
                  </>
                ) : (
                  <div className="text-center py-16 text-portal-text-secondary">
                    <PackageSearch size={48} className="mx-auto mb-4 opacity-40" />
                    <p className="text-lg">Ничего не найдено</p>
                    <p className="text-sm mt-1">Попробуйте изменить запрос</p>
                  </div>
                )}
              </>
            )}

            {!response && !loading && (
              <div className="text-center py-20 text-portal-text-secondary">
                <PackageSearch size={64} className="mx-auto mb-4 opacity-20" />
                <p className="text-lg">Начните вводить название товара</p>
                <p className="text-sm mt-1">
                  Система учтёт ваш профиль ({user.industry || "не указан"}) и историю закупок
                </p>
              </div>
            )}
          </div>
        </div>
      </main>

      <DemoSwitcher currentInn={user.inn} onSwitch={handleOnboard} />
    </div>
  );
}
