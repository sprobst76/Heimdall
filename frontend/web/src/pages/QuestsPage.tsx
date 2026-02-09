import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Trophy,
  Plus,
  CheckCircle,
  XCircle,
  Clock,
  Eye,
  Send,
  Loader2,
  AlertCircle,
  X,
  ChevronLeft,
  Pencil,
  Trash2,
} from 'lucide-react';
import { useChildren } from '../hooks/useChildren';
import {
  useQuestTemplates,
  useCreateQuestTemplate,
  useUpdateQuestTemplate,
  useDeleteQuestTemplate,
  useChildQuests,
  useAssignQuest,
  useReviewQuest,
} from '../hooks/useQuests';
import type {
  QuestTemplate,
  QuestTemplateCreate,
  QuestInstance,
  QuestReview,
} from '../types';

const FAMILY_ID = 'demo';

const CATEGORY_OPTIONS = [
  { value: 'Haushalt', label: 'Haushalt' },
  { value: 'Schule', label: 'Schule' },
  { value: 'Bonus', label: 'Bonus' },
];

const PROOF_TYPE_OPTIONS = [
  { value: 'photo', label: 'Foto' },
  { value: 'screenshot', label: 'Screenshot' },
  { value: 'parent_confirm', label: 'Eltern bestatigen' },
  { value: 'auto', label: 'Automatisch' },
  { value: 'checklist', label: 'Checkliste' },
];

const RECURRENCE_OPTIONS = [
  { value: 'daily', label: 'Taglich' },
  { value: 'weekly', label: 'Wochentlich' },
  { value: 'school_days', label: 'Schultage' },
  { value: 'once', label: 'Einmalig' },
];

function statusBadge(status: string): { label: string; color: string } {
  switch (status) {
    case 'available':
      return { label: 'Verfugbar', color: 'bg-blue-100 text-blue-700' };
    case 'claimed':
      return { label: 'Angenommen', color: 'bg-yellow-100 text-yellow-700' };
    case 'pending_review':
      return { label: 'Prufung', color: 'bg-orange-100 text-orange-700' };
    case 'approved':
      return { label: 'Genehmigt', color: 'bg-emerald-100 text-emerald-700' };
    case 'rejected':
      return { label: 'Abgelehnt', color: 'bg-red-100 text-red-700' };
    default:
      return { label: status, color: 'bg-slate-100 text-slate-600' };
  }
}

function categoryLabel(cat: string): string {
  const found = CATEGORY_OPTIONS.find((o) => o.value === cat);
  return found ? found.label : cat;
}

function proofTypeLabel(pt: string): string {
  const found = PROOF_TYPE_OPTIONS.find((o) => o.value === pt);
  return found ? found.label : pt;
}

function recurrenceLabel(r: string): string {
  const found = RECURRENCE_OPTIONS.find((o) => o.value === r);
  return found ? found.label : r;
}

export default function QuestsPage() {
  const { childId } = useParams<{ childId: string }>();
  const { data: children } = useChildren(FAMILY_ID);
  const child = children?.find((c) => c.id === childId);

  const {
    data: templates,
    isLoading: templatesLoading,
    isError: templatesError,
    error: templatesErr,
  } = useQuestTemplates(FAMILY_ID);
  const {
    data: instances,
    isLoading: instancesLoading,
    isError: instancesError,
    error: instancesErr,
  } = useChildQuests(childId ?? '');

  const createTemplate = useCreateQuestTemplate(FAMILY_ID);
  const updateTemplate = useUpdateQuestTemplate(FAMILY_ID);
  const deleteTemplate = useDeleteQuestTemplate(FAMILY_ID);
  const assignQuest = useAssignQuest(childId ?? '');
  const reviewQuest = useReviewQuest(childId ?? '');

  // Template form state
  const [showForm, setShowForm] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<QuestTemplate | null>(
    null
  );
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  const [formName, setFormName] = useState('');
  const [formDescription, setFormDescription] = useState('');
  const [formCategory, setFormCategory] = useState('Haushalt');
  const [formRewardMinutes, setFormRewardMinutes] = useState('15');
  const [formProofType, setFormProofType] = useState('parent_confirm');
  const [formRecurrence, setFormRecurrence] = useState('daily');
  const [formError, setFormError] = useState('');

  // Review state
  const [reviewingInstance, setReviewingInstance] =
    useState<QuestInstance | null>(null);
  const [reviewFeedback, setReviewFeedback] = useState('');
  const [reviewError, setReviewError] = useState('');

  // Assign state
  const [showAssign, setShowAssign] = useState(false);

  function openCreateForm() {
    setEditingTemplate(null);
    setFormName('');
    setFormDescription('');
    setFormCategory('Haushalt');
    setFormRewardMinutes('15');
    setFormProofType('parent_confirm');
    setFormRecurrence('daily');
    setFormError('');
    setShowForm(true);
  }

  function openEditForm(template: QuestTemplate) {
    setEditingTemplate(template);
    setFormName(template.name);
    setFormDescription(template.description ?? '');
    setFormCategory(template.category);
    setFormRewardMinutes(String(template.reward_minutes));
    setFormProofType(template.proof_type);
    setFormRecurrence(template.recurrence);
    setFormError('');
    setShowForm(true);
  }

  function closeForm() {
    setShowForm(false);
    setEditingTemplate(null);
    setFormError('');
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError('');

    if (!formName.trim()) {
      setFormError('Name ist erforderlich');
      return;
    }
    const reward = parseInt(formRewardMinutes);
    if (!reward || reward <= 0) {
      setFormError('Belohnung muss grosser als 0 sein');
      return;
    }

    try {
      if (editingTemplate) {
        await updateTemplate.mutateAsync({
          questId: editingTemplate.id,
          data: {
            name: formName.trim(),
            description: formDescription.trim() || null,
            category: formCategory,
            reward_minutes: reward,
            proof_type: formProofType,
            recurrence: formRecurrence,
          },
        });
      } else {
        const payload: QuestTemplateCreate = {
          name: formName.trim(),
          description: formDescription.trim() || null,
          category: formCategory,
          reward_minutes: reward,
          proof_type: formProofType,
          recurrence: formRecurrence,
        };
        await createTemplate.mutateAsync(payload);
      }
      closeForm();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? 'Vorgang fehlgeschlagen';
      setFormError(msg);
    }
  }

  async function handleDelete(questId: string) {
    try {
      await deleteTemplate.mutateAsync(questId);
      setDeleteConfirm(null);
    } catch {
      // silent
    }
  }

  async function handleToggleActive(template: QuestTemplate) {
    await updateTemplate.mutateAsync({
      questId: template.id,
      data: { active: !template.active },
    });
  }

  async function handleAssign(templateId: string) {
    try {
      await assignQuest.mutateAsync(templateId);
      setShowAssign(false);
    } catch {
      // silent
    }
  }

  function openReview(instance: QuestInstance) {
    setReviewingInstance(instance);
    setReviewFeedback('');
    setReviewError('');
  }

  function closeReview() {
    setReviewingInstance(null);
    setReviewFeedback('');
    setReviewError('');
  }

  async function handleReview(approved: boolean) {
    if (!reviewingInstance) return;
    setReviewError('');

    const payload: QuestReview = {
      approved,
      feedback: reviewFeedback.trim() || null,
    };

    try {
      await reviewQuest.mutateAsync({
        instanceId: reviewingInstance.id,
        data: payload,
      });
      closeReview();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? 'Bewertung fehlgeschlagen';
      setReviewError(msg);
    }
  }

  // Helper: resolve template name for an instance
  function templateName(instance: QuestInstance): string {
    const tmpl = templates?.find((t) => t.id === instance.template_id);
    return tmpl?.name ?? 'Unbekannte Quest';
  }

  if (!childId) {
    return (
      <div className="py-12 text-center text-sm text-slate-500">
        Kein Kind ausgewahlt.
      </div>
    );
  }

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
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Quests{child ? ` - ${child.name}` : ''}
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Quest-Vorlagen und zugewiesene Aufgaben verwalten
          </p>
        </div>
        <button
          onClick={openCreateForm}
          className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-indigo-700"
        >
          <Plus className="h-4 w-4" />
          Neue Quest-Vorlage
        </button>
      </div>

      {/* ── Quest Templates Section ──────────────────────────────────────── */}
      <div className="mb-8">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-800">
            Quest-Vorlagen
          </h2>
        </div>

        {/* Loading */}
        {templatesLoading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
          </div>
        )}

        {/* Error */}
        {templatesError && (
          <div className="flex flex-col items-center justify-center rounded-xl border border-red-200 bg-red-50 py-12">
            <AlertCircle className="mb-3 h-8 w-8 text-red-400" />
            <p className="text-sm font-medium text-red-700">
              Fehler:{' '}
              {(templatesErr as Error)?.message ?? 'Unbekannter Fehler'}
            </p>
          </div>
        )}

        {/* Empty state */}
        {!templatesLoading &&
          !templatesError &&
          templates &&
          templates.length === 0 && (
            <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-300 bg-white py-16">
              <Trophy className="mb-4 h-12 w-12 text-slate-300" />
              <h3 className="text-lg font-semibold text-slate-700">
                Keine Quest-Vorlagen vorhanden
              </h3>
              <p className="mt-1 text-sm text-slate-500">
                Erstellen Sie die erste Quest-Vorlage fur Ihre Familie.
              </p>
            </div>
          )}

        {/* Templates list */}
        <div className="space-y-3">
          {templates?.map((template) => (
            <div
              key={template.id}
              className={`rounded-xl border bg-white p-5 shadow-sm transition-all ${
                template.active
                  ? 'border-slate-200'
                  : 'border-slate-200 opacity-60'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <h3 className="text-base font-semibold text-slate-900">
                      {template.name}
                    </h3>
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                        template.active
                          ? 'bg-emerald-100 text-emerald-700'
                          : 'bg-slate-100 text-slate-500'
                      }`}
                    >
                      {template.active ? 'Aktiv' : 'Inaktiv'}
                    </span>
                    <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-600">
                      {categoryLabel(template.category)}
                    </span>
                  </div>

                  {template.description && (
                    <p className="mt-1 text-sm text-slate-500">
                      {template.description}
                    </p>
                  )}

                  <div className="mt-2 flex flex-wrap gap-3 text-sm text-slate-600">
                    <span className="flex items-center gap-1">
                      <Clock className="h-3.5 w-3.5 text-slate-400" />
                      {template.reward_minutes} Min. Belohnung
                    </span>
                    <span className="flex items-center gap-1">
                      <Eye className="h-3.5 w-3.5 text-slate-400" />
                      {proofTypeLabel(template.proof_type)}
                    </span>
                    <span className="text-xs text-slate-400">
                      {recurrenceLabel(template.recurrence)}
                    </span>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => handleAssign(template.id)}
                    disabled={assignQuest.isPending || !template.active}
                    className="rounded-lg p-2 text-indigo-500 transition-colors hover:bg-indigo-50 hover:text-indigo-700 disabled:opacity-50"
                    title="Zuweisen"
                  >
                    <Send className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => handleToggleActive(template)}
                    className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"
                    title={template.active ? 'Deaktivieren' : 'Aktivieren'}
                  >
                    {template.active ? (
                      <CheckCircle className="h-4 w-4 text-emerald-500" />
                    ) : (
                      <XCircle className="h-4 w-4" />
                    )}
                  </button>
                  <button
                    onClick={() => openEditForm(template)}
                    className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"
                    title="Bearbeiten"
                  >
                    <Pencil className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => setDeleteConfirm(template.id)}
                    className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-red-50 hover:text-red-500"
                    title="Loschen"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>

              {/* Delete confirm */}
              {deleteConfirm === template.id && (
                <div className="mt-4 flex items-center justify-between rounded-lg bg-red-50 px-4 py-3">
                  <p className="text-sm text-red-700">
                    Quest-Vorlage wirklich loschen?
                  </p>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setDeleteConfirm(null)}
                      className="rounded-md px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100"
                    >
                      Abbrechen
                    </button>
                    <button
                      onClick={() => handleDelete(template.id)}
                      disabled={deleteTemplate.isPending}
                      className="flex items-center gap-1 rounded-md bg-red-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-700 disabled:opacity-50"
                    >
                      {deleteTemplate.isPending && (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      )}
                      Loschen
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* ── Quest Instances Section ──────────────────────────────────────── */}
      <div>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-800">
            Zugewiesene Quests
          </h2>
          <button
            onClick={() => setShowAssign(true)}
            className="flex items-center gap-1.5 text-sm font-medium text-indigo-600 hover:text-indigo-700"
          >
            <Plus className="h-3.5 w-3.5" />
            Quest zuweisen
          </button>
        </div>

        {/* Loading */}
        {instancesLoading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
          </div>
        )}

        {/* Error */}
        {instancesError && (
          <div className="flex flex-col items-center justify-center rounded-xl border border-red-200 bg-red-50 py-12">
            <AlertCircle className="mb-3 h-8 w-8 text-red-400" />
            <p className="text-sm font-medium text-red-700">
              Fehler:{' '}
              {(instancesErr as Error)?.message ?? 'Unbekannter Fehler'}
            </p>
          </div>
        )}

        {/* Empty state */}
        {!instancesLoading &&
          !instancesError &&
          instances &&
          instances.length === 0 && (
            <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-300 bg-white py-12">
              <Trophy className="mb-4 h-10 w-10 text-slate-300" />
              <h3 className="text-base font-semibold text-slate-700">
                Keine zugewiesenen Quests
              </h3>
              <p className="mt-1 text-sm text-slate-500">
                Weisen Sie diesem Kind eine Quest-Vorlage zu.
              </p>
            </div>
          )}

        {/* Instances list */}
        <div className="space-y-3">
          {instances?.map((instance) => {
            const badge = statusBadge(instance.status);
            return (
              <div
                key={instance.id}
                className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3">
                      <Trophy className="h-5 w-5 text-amber-500" />
                      <h3 className="text-base font-semibold text-slate-900">
                        {templateName(instance)}
                      </h3>
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${badge.color}`}
                      >
                        {badge.label}
                      </span>
                    </div>

                    <div className="mt-2 flex flex-wrap gap-3 text-xs text-slate-400">
                      <span>
                        Erstellt:{' '}
                        {new Date(instance.created_at).toLocaleString('de-DE', {
                          dateStyle: 'short',
                          timeStyle: 'short',
                        })}
                      </span>
                      {instance.claimed_at && (
                        <span>
                          Angenommen:{' '}
                          {new Date(instance.claimed_at).toLocaleString(
                            'de-DE',
                            { dateStyle: 'short', timeStyle: 'short' }
                          )}
                        </span>
                      )}
                      {instance.proof_url && (
                        <a
                          href={instance.proof_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1 text-indigo-500 hover:text-indigo-700"
                        >
                          <Eye className="h-3 w-3" />
                          Beweis anzeigen
                        </a>
                      )}
                    </div>
                  </div>

                  {/* Review button for pending_review */}
                  {instance.status === 'pending_review' && (
                    <button
                      onClick={() => openReview(instance)}
                      className="flex items-center gap-1.5 rounded-lg bg-orange-50 px-3 py-2 text-xs font-medium text-orange-700 transition-colors hover:bg-orange-100"
                    >
                      <Eye className="h-3.5 w-3.5" />
                      Prufen
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Assign Quest Modal ───────────────────────────────────────────── */}
      {showAssign && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
          <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white p-6 shadow-xl">
            <div className="mb-5 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900">
                Quest zuweisen
              </h2>
              <button
                onClick={() => setShowAssign(false)}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {templates && templates.filter((t) => t.active).length === 0 ? (
              <p className="py-8 text-center text-sm text-slate-500">
                Keine aktiven Quest-Vorlagen vorhanden.
              </p>
            ) : (
              <div className="space-y-2">
                {templates
                  ?.filter((t) => t.active)
                  .map((template) => (
                    <button
                      key={template.id}
                      onClick={() => handleAssign(template.id)}
                      disabled={assignQuest.isPending}
                      className="flex w-full items-center justify-between rounded-lg border border-slate-200 p-4 text-left transition-colors hover:bg-slate-50 disabled:opacity-50"
                    >
                      <div>
                        <h4 className="text-sm font-semibold text-slate-900">
                          {template.name}
                        </h4>
                        <p className="text-xs text-slate-500">
                          {categoryLabel(template.category)} &middot;{' '}
                          {template.reward_minutes} Min. &middot;{' '}
                          {recurrenceLabel(template.recurrence)}
                        </p>
                      </div>
                      <Send className="h-4 w-4 text-indigo-500" />
                    </button>
                  ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Review Modal ─────────────────────────────────────────────────── */}
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

            <div className="mb-4 rounded-lg bg-slate-50 p-4">
              <h3 className="text-sm font-semibold text-slate-900">
                {templateName(reviewingInstance)}
              </h3>
              {reviewingInstance.proof_url && (
                <a
                  href={reviewingInstance.proof_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-2 inline-flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-700"
                >
                  <Eye className="h-3 w-3" />
                  Beweis anzeigen
                </a>
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
          </div>
        </div>
      )}

      {/* ── Create/Edit Template Modal ───────────────────────────────────── */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
          <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white p-6 shadow-xl">
            <div className="mb-5 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900">
                {editingTemplate
                  ? 'Quest-Vorlage bearbeiten'
                  : 'Quest-Vorlage erstellen'}
              </h2>
              <button
                onClick={closeForm}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {formError && (
              <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
                {formError}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Name */}
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  Name *
                </label>
                <input
                  type="text"
                  required
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder="z.B. Zimmer aufraumen"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                />
              </div>

              {/* Description */}
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  Beschreibung
                </label>
                <textarea
                  value={formDescription}
                  onChange={(e) => setFormDescription(e.target.value)}
                  rows={2}
                  placeholder="Was muss gemacht werden?"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                />
              </div>

              {/* Category */}
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  Kategorie
                </label>
                <select
                  value={formCategory}
                  onChange={(e) => setFormCategory(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                >
                  {CATEGORY_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Reward minutes */}
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  Belohnung (Minuten) *
                </label>
                <input
                  type="number"
                  min="1"
                  required
                  value={formRewardMinutes}
                  onChange={(e) => setFormRewardMinutes(e.target.value)}
                  placeholder="z.B. 15"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                />
              </div>

              {/* Proof type */}
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  Nachweis-Typ
                </label>
                <select
                  value={formProofType}
                  onChange={(e) => setFormProofType(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                >
                  {PROOF_TYPE_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Recurrence */}
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  Wiederholung
                </label>
                <select
                  value={formRecurrence}
                  onChange={(e) => setFormRecurrence(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                >
                  {RECURRENCE_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Submit */}
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={closeForm}
                  className="flex-1 rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
                >
                  Abbrechen
                </button>
                <button
                  type="submit"
                  disabled={
                    createTemplate.isPending || updateTemplate.isPending
                  }
                  className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
                >
                  {(createTemplate.isPending || updateTemplate.isPending) && (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  )}
                  {editingTemplate ? 'Speichern' : 'Erstellen'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
