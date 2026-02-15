import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Trophy,
  CheckCircle,
  XCircle,
  Eye,
  Loader2,
  AlertCircle,
  X,
  ChevronLeft,
  Clock,
} from 'lucide-react';
import { useChildren } from '../hooks/useChildren';
import {
  useQuestTemplates,
  useChildQuests,
  useReviewQuest,
} from '../hooks/useQuests';
import { useFamilyId } from '../hooks/useAuth';
import type { QuestInstance, QuestReview, QuestTemplate, User } from '../types';

function ChildReviewSection({
  child,
  templates,
  onCountChange,
}: {
  child: User;
  templates: QuestTemplate[] | undefined;
  onCountChange: (childId: string, count: number) => void;
}) {
  const {
    data: instances,
    isLoading,
    isError,
    error,
  } = useChildQuests(child.id, 'pending_review');
  const reviewQuest = useReviewQuest(child.id);

  useEffect(() => {
    onCountChange(child.id, instances?.length ?? 0);
  }, [instances?.length, child.id, onCountChange]);

  const [reviewingInstance, setReviewingInstance] =
    useState<QuestInstance | null>(null);
  const [reviewFeedback, setReviewFeedback] = useState('');
  const [reviewError, setReviewError] = useState('');
  const [successTan, setSuccessTan] = useState<string | null>(null);

  function templateName(instance: QuestInstance): string {
    const tmpl = templates?.find((t) => t.id === instance.template_id);
    return tmpl?.name ?? 'Unbekannte Quest';
  }

  function openReview(instance: QuestInstance) {
    setReviewingInstance(instance);
    setReviewFeedback('');
    setReviewError('');
    setSuccessTan(null);
  }

  function closeReview() {
    setReviewingInstance(null);
    setReviewFeedback('');
    setReviewError('');
    setSuccessTan(null);
  }

  async function handleReview(approved: boolean) {
    if (!reviewingInstance) return;
    setReviewError('');

    const payload: QuestReview = {
      approved,
      feedback: reviewFeedback.trim() || null,
    };

    try {
      const result = await reviewQuest.mutateAsync({
        instanceId: reviewingInstance.id,
        data: payload,
      });
      if (approved && result.data?.generated_tan_id) {
        setSuccessTan(result.data.generated_tan_id);
      } else if (approved) {
        setSuccessTan('Genehmigt');
      } else {
        closeReview();
      }
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? 'Bewertung fehlgeschlagen';
      setReviewError(msg);
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-indigo-600" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4">
        <p className="text-sm text-red-700">
          Fehler: {(error as Error)?.message ?? 'Unbekannter Fehler'}
        </p>
      </div>
    );
  }

  if (!instances || instances.length === 0) {
    return null;
  }

  return (
    <div className="mb-6">
      <div className="mb-3 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-indigo-100 text-sm font-bold text-indigo-600">
          {child.name.charAt(0).toUpperCase()}
        </div>
        <div>
          <h3 className="text-base font-semibold text-slate-900">
            {child.name}
          </h3>
          <p className="text-xs text-slate-500">
            {instances.length}{' '}
            {instances.length === 1 ? 'Quest' : 'Quests'} zur Prufung
          </p>
        </div>
      </div>

      <div className="space-y-3 pl-13">
        {instances.map((instance) => (
          <div
            key={instance.id}
            className="rounded-xl border border-orange-200 bg-white p-4 shadow-sm"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <Trophy className="h-4 w-4 text-amber-500" />
                  <h4 className="text-sm font-semibold text-slate-900">
                    {templateName(instance)}
                  </h4>
                  <span className="rounded-full bg-orange-100 px-2 py-0.5 text-xs font-medium text-orange-700">
                    Prufung ausstehend
                  </span>
                </div>

                <div className="mt-2 flex flex-wrap gap-3 text-xs text-slate-400">
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    Eingereicht:{' '}
                    {instance.claimed_at
                      ? new Date(instance.claimed_at).toLocaleString('de-DE', {
                          dateStyle: 'short',
                          timeStyle: 'short',
                        })
                      : new Date(instance.created_at).toLocaleString('de-DE', {
                          dateStyle: 'short',
                          timeStyle: 'short',
                        })}
                  </span>
                </div>

                {/* Proof image */}
                {instance.proof_url && (
                  <div className="mt-3">
                    <a
                      href={instance.proof_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="group inline-block"
                    >
                      <img
                        src={instance.proof_url}
                        alt="Beweis"
                        className="h-32 w-auto rounded-lg border border-slate-200 object-cover transition-opacity group-hover:opacity-80"
                      />
                    </a>
                  </div>
                )}
              </div>

              <button
                onClick={() => openReview(instance)}
                className="flex items-center gap-1.5 rounded-lg bg-orange-50 px-3 py-2 text-xs font-medium text-orange-700 transition-colors hover:bg-orange-100"
              >
                <Eye className="h-3.5 w-3.5" />
                Prufen
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Review Modal */}
      {reviewingInstance && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
            <div className="mb-5 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900">
                Quest prufen
              </h2>
              <button
                onClick={closeReview}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Success state */}
            {successTan && (
              <div className="mb-4">
                <div className="flex flex-col items-center rounded-xl bg-emerald-50 p-6">
                  <CheckCircle className="mb-2 h-10 w-10 text-emerald-500" />
                  <p className="mb-1 text-sm font-medium text-emerald-700">
                    Quest genehmigt!
                  </p>
                  {successTan !== 'Genehmigt' && (
                    <p className="text-xs text-emerald-600">
                      TAN-ID: {successTan}
                    </p>
                  )}
                </div>
                <button
                  onClick={closeReview}
                  className="mt-4 w-full rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
                >
                  Schliessen
                </button>
              </div>
            )}

            {/* Review form */}
            {!successTan && (
              <>
                <div className="mb-4 rounded-lg bg-slate-50 p-4">
                  <h3 className="text-sm font-semibold text-slate-900">
                    {templateName(reviewingInstance)}
                  </h3>
                  <p className="mt-1 text-xs text-slate-500">
                    Kind: {child.name}
                  </p>
                  {reviewingInstance.proof_url && (
                    <div className="mt-3">
                      <a
                        href={reviewingInstance.proof_url}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <img
                          src={reviewingInstance.proof_url}
                          alt="Beweis"
                          className="h-40 w-auto rounded-lg border border-slate-200 object-cover"
                        />
                      </a>
                    </div>
                  )}
                </div>

                {reviewError && (
                  <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
                    {reviewError}
                  </div>
                )}

                <div className="mb-4">
                  <label className="mb-1 block text-sm font-medium text-slate-700">
                    Feedback (optional)
                  </label>
                  <textarea
                    value={reviewFeedback}
                    onChange={(e) => setReviewFeedback(e.target.value)}
                    rows={3}
                    placeholder="Optionaler Kommentar..."
                    className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                  />
                </div>

                <div className="flex gap-3">
                  <button
                    onClick={() => handleReview(false)}
                    disabled={reviewQuest.isPending}
                    className="flex flex-1 items-center justify-center gap-2 rounded-lg border border-red-300 px-4 py-2.5 text-sm font-medium text-red-700 transition-colors hover:bg-red-50 disabled:opacity-50"
                  >
                    {reviewQuest.isPending && (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    )}
                    <XCircle className="h-4 w-4" />
                    Ablehnen
                  </button>
                  <button
                    onClick={() => handleReview(true)}
                    disabled={reviewQuest.isPending}
                    className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-emerald-700 disabled:opacity-50"
                  >
                    {reviewQuest.isPending && (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    )}
                    <CheckCircle className="h-4 w-4" />
                    Genehmigen
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function QuestReviewPage() {
  const familyId = useFamilyId();
  const {
    data: children,
    isLoading: childrenLoading,
    isError: childrenError,
    error: childrenErr,
  } = useChildren(familyId);
  const { data: templates } = useQuestTemplates(familyId);

  const [pendingCounts, setPendingCounts] = useState<Record<string, number>>(
    {}
  );

  function handleCountChange(childId: string, count: number) {
    setPendingCounts((prev) => {
      if (prev[childId] === count) return prev;
      return { ...prev, [childId]: count };
    });
  }

  const totalPending = Object.values(pendingCounts).reduce(
    (sum, c) => sum + c,
    0
  );

  return (
    <div className="mx-auto max-w-4xl">
      {/* Back link */}
      <Link
        to="/"
        className="mb-4 inline-flex items-center gap-1 text-sm font-medium text-slate-500 hover:text-indigo-600"
      >
        <ChevronLeft className="h-4 w-4" />
        Zuruck zum Dashboard
      </Link>

      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">
          Quest-Prufungen
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Eingereichte Quests aller Kinder prufen und genehmigen
        </p>
      </div>

      {/* Loading */}
      {childrenLoading && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
        </div>
      )}

      {/* Error */}
      {childrenError && (
        <div className="flex flex-col items-center justify-center rounded-xl border border-red-200 bg-red-50 py-12">
          <AlertCircle className="mb-3 h-8 w-8 text-red-400" />
          <p className="text-sm font-medium text-red-700">
            Fehler:{' '}
            {(childrenErr as Error)?.message ?? 'Unbekannter Fehler'}
          </p>
        </div>
      )}

      {/* Children sections */}
      {!childrenLoading && !childrenError && children && (
        <>
          {children.map((child) => (
            <ChildReviewSection
              key={child.id}
              child={child}
              templates={templates}
              onCountChange={handleCountChange}
            />
          ))}

          {/* Empty state when no child has pending quests */}
          {children.length > 0 && totalPending === 0 && (
            <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-300 bg-white py-16">
              <Trophy className="mb-4 h-12 w-12 text-slate-300" />
              <h3 className="text-lg font-semibold text-slate-700">
                Keine Quests zur Prufung
              </h3>
              <p className="mt-1 text-sm text-slate-500">
                Alle eingereichten Quests wurden bereits gepruft.
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
