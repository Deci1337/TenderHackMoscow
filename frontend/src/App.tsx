import { useCallback, useState } from "react";
import { api } from "./api/client";
import CompareModal from "./components/CompareModal";
import CompareTray from "./components/CompareTray";
import DemoSwitcher from "./components/DemoSwitcher";
import EmptyState from "./components/EmptyState";
import FilterPanel from "./components/FilterPanel";
import Header from "./components/Header";
import OnboardingModal from "./components/OnboardingModal";
import Pagination from "./components/Pagination";
import ProfilePanel from "./components/ProfilePanel";
import RankingChangeNotice from "./components/RankingChangeNotice";
import SearchBar from "./components/SearchBar";
import SortDropdown, { SortBy } from "./components/SortDropdown";
import STECard from "./components/STECard";
import STECardSkeleton from "./components/STECardSkeleton";
import Toast from "./components/Toast";
import { useCompare } from "./hooks/useCompare";
import { useEvents } from "./hooks/useEvents";
import { useSearch } from "./hooks/useSearch";
import { useToast } from "./hooks/useToast";

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
  const [sortBy, setSortBy] = useState<SortBy>("relevance");
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [showCompare, setShowCompare] = useState(false);

  const { response, loading, search } = useSearch(user?.inn || "", sessionId);
  const { trackClick, trackBounce, track } = useEvents(user?.inn || "", sessionId);
  const { toasts, addToast, removeToast } = useToast();
  const compare = useCompare();

  const handleOnboard = useCallback(
    async (inn: string, name: string, industry: string) => {
      try { await api.onboard(inn, name, undefined, industry); } catch { /* offline dev */ }
      setUser({ inn, name, industry });
    },
    []
  );

  const handleSearch = useCallback(
    (query: string, newOffset = 0, newSort = sortBy, newCat = selectedCategory) => {
      setLastQuery(query);
      setOffset(newOffset);
      search(query, newOffset, PAGE_SIZE, newSort, newCat ?? undefined);
    },
    [search, sortBy, selectedCategory]
  );

  const handleSortChange = useCallback(
    (newSort: SortBy) => {
      setSortBy(newSort);
      if (lastQuery) handleSearch(lastQuery, 0, newSort, selectedCategory);
    },
    [lastQuery, selectedCategory, handleSearch]
  );

  const handleCategoryChange = useCallback(
    (cat: string | null) => {
      setSelectedCategory(cat);
      if (lastQuery) handleSearch(lastQuery, 0, sortBy, cat);
    },
    [lastQuery, sortBy, handleSearch]
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
      const item = response?.results.find((r) => r.id === steId);
      if (action === "compare" && item) {
        if (compare.has(steId)) {
          compare.remove(steId);
          addToast("Убрано из сравнения", "info");
        } else if (compare.isFull) {
          addToast("Максимум 3 товара для сравнения", "warning");
        } else {
          compare.add(item);
          addToast("Добавлено к сравнению", "success");
        }
      }
      if (action === "hide") addToast("Товар скрыт — выдача обновится при следующем поиске", "warning");
      if (action === "like") addToast("Добавлено в избранное", "success");
    },
    [track, trackClick, trackBounce, lastQuery, response, compare, addToast]
  );

  if (!user) {
    return <OnboardingModal onComplete={handleOnboard} />;
  }

  return (
    <div className="min-h-screen bg-portal-bg">
      <Header currentUser={user} onSwitchUser={() => setUser(null)} />

      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="mb-6">
          <h2 className="text-xl font-bold text-portal-text mb-1">Поиск по каталогу СТЕ</h2>
          <p className="text-portal-text-secondary text-sm">
            Персонализированный поиск с учётом истории закупок и поведения пользователя
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
            <FilterPanel
              selectedCategory={selectedCategory}
              onSelect={handleCategoryChange}
            />
          </aside>

          {/* Results */}
          <div className="flex-1 min-w-0">
            {response?.did_you_mean && (
              <div className="mb-4">
                <RankingChangeNotice reason={response.did_you_mean} />
              </div>
            )}

            {/* Sort bar — показываем только если есть результаты */}
            {(response || loading) && (
              <div className="mb-4">
                <SortDropdown
                  value={sortBy}
                  onChange={handleSortChange}
                  total={response?.total}
                />
              </div>
            )}

            {/* Loading skeletons */}
            {loading && (
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {Array.from({ length: 6 }).map((_, i) => <STECardSkeleton key={i} />)}
              </div>
            )}

            {!loading && response && (
              <>
                {response.results.length > 0 ? (
                  <>
                    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                      {response.results.map((item) => (
                        <STECard
                          key={item.id}
                          item={item}
                          query={lastQuery}
                          onAction={handleAction}
                          inCompare={compare.has(item.id)}
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
                  <EmptyState query={lastQuery} onQueryClick={(q) => handleSearch(q, 0)} />
                )}
              </>
            )}

            {!response && !loading && (
              <div className="text-center py-20 text-portal-text-secondary">
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

      {/* Compare tray — sticky bottom bar */}
      <CompareTray
        items={compare.items}
        onRemove={compare.remove}
        onOpen={() => setShowCompare(true)}
        onClear={compare.clear}
      />

      {/* Compare modal */}
      {showCompare && (
        <CompareModal items={compare.items} onClose={() => setShowCompare(false)} />
      )}

      <Toast toasts={toasts} onRemove={removeToast} />
    </div>
  );
}
