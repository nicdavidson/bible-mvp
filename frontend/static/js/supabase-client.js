/**
 * Supabase Client for BibleMVP
 * Handles authentication and notes sync
 */

const SUPABASE_URL = 'https://grhmoooaegtulfpahnpy.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdyaG1vb29hZWd0dWxmcGFobnB5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njg3NzY2NzksImV4cCI6MjA4NDM1MjY3OX0.UA5IP0BudscfANQRzMZB76k3SQS-kNKWjyzEzHdBh80';

// Initialize Supabase client (loaded from CDN in HTML head)
const supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// Auth functions
async function getUser() {
    const { data: { user } } = await supabaseClient.auth.getUser();
    return user;
}

async function signUp(email, password) {
    const { data, error } = await supabaseClient.auth.signUp({
        email,
        password
    });
    if (error) throw error;
    return data;
}

async function signIn(email, password) {
    const { data, error } = await supabaseClient.auth.signInWithPassword({
        email,
        password
    });
    if (error) throw error;
    return data;
}

async function signOut() {
    const { error } = await supabaseClient.auth.signOut();
    if (error) throw error;
}

async function resetPassword(email) {
    const { data, error } = await supabaseClient.auth.resetPasswordForEmail(email, {
        redirectTo: window.location.origin
    });
    if (error) throw error;
    return data;
}

// Notes sync functions
async function fetchUserNotes() {
    const user = await getUser();
    if (!user) return [];

    const { data, error } = await supabaseClient
        .from('user_notes')
        .select('*')
        .eq('user_id', user.id)
        .order('created_at', { ascending: false });

    if (error) throw error;

    // Map to frontend format
    return data.map(note => ({
        id: note.id,
        book: note.book,
        chapter: note.chapter,
        startVerse: note.start_verse,
        endVerse: note.end_verse,
        content: note.content,
        created_at: note.created_at,
        synced: true
    }));
}

async function saveUserNote(note) {
    const user = await getUser();
    if (!user) throw new Error('Not authenticated');

    const { data, error } = await supabaseClient
        .from('user_notes')
        .insert({
            user_id: user.id,
            book: note.book,
            chapter: note.chapter,
            start_verse: note.startVerse,
            end_verse: note.endVerse || note.startVerse,
            content: note.content
        })
        .select()
        .single();

    if (error) throw error;

    return {
        id: data.id,
        book: data.book,
        chapter: data.chapter,
        startVerse: data.start_verse,
        endVerse: data.end_verse,
        content: data.content,
        created_at: data.created_at,
        synced: true
    };
}

async function deleteUserNote(noteId) {
    const user = await getUser();
    if (!user) throw new Error('Not authenticated');

    const { error } = await supabaseClient
        .from('user_notes')
        .delete()
        .eq('id', noteId)
        .eq('user_id', user.id);

    if (error) throw error;
}

async function updateUserNote(noteId, updates) {
    const user = await getUser();
    if (!user) throw new Error('Not authenticated');

    const updateData = {};
    if (updates.content !== undefined) updateData.content = updates.content;

    const { data, error } = await supabaseClient
        .from('user_notes')
        .update(updateData)
        .eq('id', noteId)
        .eq('user_id', user.id)
        .select()
        .single();

    if (error) throw error;

    return {
        id: data.id,
        book: data.book,
        chapter: data.chapter,
        startVerse: data.start_verse,
        endVerse: data.end_verse,
        content: data.content,
        created_at: data.created_at,
        synced: true
    };
}

async function syncLocalNotesToSupabase(localNotes) {
    const user = await getUser();
    if (!user) return { synced: 0, errors: [] };

    let synced = 0;
    const errors = [];

    for (const note of localNotes) {
        // Skip already synced notes (they have numeric IDs from Supabase)
        if (note.synced) continue;

        try {
            await supabaseClient
                .from('user_notes')
                .insert({
                    user_id: user.id,
                    book: note.book,
                    chapter: note.chapter,
                    start_verse: note.startVerse,
                    end_verse: note.endVerse || note.startVerse,
                    content: note.content,
                    created_at: note.created_at
                });
            synced++;
        } catch (err) {
            errors.push({ note, error: err.message });
        }
    }

    return { synced, errors };
}

// Tag sync functions
async function fetchUserTags() {
    const user = await getUser();
    if (!user) return [];

    const { data, error } = await supabaseClient
        .from('user_tags')
        .select('*')
        .eq('user_id', user.id)
        .order('sort_order', { ascending: true });

    if (error) throw error;

    return data.map(tag => ({
        id: tag.id,
        name: tag.name,
        color: tag.color,
        sortOrder: tag.sort_order,
        synced: true
    }));
}

async function createUserTag(name, color) {
    const user = await getUser();
    if (!user) throw new Error('Not authenticated');

    const { data, error } = await supabaseClient
        .from('user_tags')
        .insert({
            user_id: user.id,
            name,
            color
        })
        .select()
        .single();

    if (error) throw error;

    return {
        id: data.id,
        name: data.name,
        color: data.color,
        sortOrder: data.sort_order,
        synced: true
    };
}

async function updateUserTag(tagId, updates) {
    const user = await getUser();
    if (!user) throw new Error('Not authenticated');

    const updateData = {};
    if (updates.name !== undefined) updateData.name = updates.name;
    if (updates.color !== undefined) updateData.color = updates.color;
    if (updates.sortOrder !== undefined) updateData.sort_order = updates.sortOrder;

    const { data, error } = await supabaseClient
        .from('user_tags')
        .update(updateData)
        .eq('id', tagId)
        .eq('user_id', user.id)
        .select()
        .single();

    if (error) throw error;

    return {
        id: data.id,
        name: data.name,
        color: data.color,
        sortOrder: data.sort_order,
        synced: true
    };
}

async function deleteUserTag(tagId) {
    const user = await getUser();
    if (!user) throw new Error('Not authenticated');

    const { error } = await supabaseClient
        .from('user_tags')
        .delete()
        .eq('id', tagId)
        .eq('user_id', user.id);

    if (error) throw error;
}

async function addTagToNote(noteId, tagId) {
    const user = await getUser();
    if (!user) throw new Error('Not authenticated');

    const { error } = await supabaseClient
        .from('note_tags')
        .insert({
            note_id: noteId,
            tag_id: tagId
        });

    if (error) throw error;
}

async function removeTagFromNote(noteId, tagId) {
    const user = await getUser();
    if (!user) throw new Error('Not authenticated');

    const { error } = await supabaseClient
        .from('note_tags')
        .delete()
        .eq('note_id', noteId)
        .eq('tag_id', tagId);

    if (error) throw error;
}

async function fetchNoteTagIds(noteId) {
    const user = await getUser();
    if (!user) return [];

    const { data, error } = await supabaseClient
        .from('note_tags')
        .select('tag_id')
        .eq('note_id', noteId);

    if (error) throw error;

    return data.map(row => row.tag_id);
}

async function fetchAllNoteTags() {
    const user = await getUser();
    if (!user) return {};

    const { data, error } = await supabaseClient
        .from('note_tags')
        .select('note_id, tag_id');

    if (error) throw error;

    // Group by note_id
    const noteTagsMap = {};
    for (const row of data) {
        if (!noteTagsMap[row.note_id]) {
            noteTagsMap[row.note_id] = [];
        }
        noteTagsMap[row.note_id].push(row.tag_id);
    }
    return noteTagsMap;
}

async function setNoteTagIds(noteId, tagIds) {
    const user = await getUser();
    if (!user) throw new Error('Not authenticated');

    // Delete all existing tags for this note
    const { error: deleteError } = await supabaseClient
        .from('note_tags')
        .delete()
        .eq('note_id', noteId);

    if (deleteError) throw deleteError;

    // Insert new tags
    if (tagIds.length > 0) {
        const { error: insertError } = await supabaseClient
            .from('note_tags')
            .insert(tagIds.map(tagId => ({
                note_id: noteId,
                tag_id: tagId
            })));

        if (insertError) throw insertError;
    }
}

// Listen for auth state changes
function onAuthStateChange(callback) {
    return supabaseClient.auth.onAuthStateChange((event, session) => {
        callback(event, session?.user || null);
    });
}

// ========== Reading Plan Functions ==========

// Fetch user's subscribed reading plans
async function fetchUserReadingPlans() {
    const user = await getUser();
    if (!user) return [];

    const { data, error } = await supabaseClient
        .from('user_reading_plans')
        .select('*')
        .eq('user_id', user.id)
        .order('created_at', { ascending: false });

    if (error) throw error;

    return data.map(plan => ({
        id: plan.id,
        planId: plan.plan_id,
        startDate: plan.start_date,
        isActive: plan.is_active,
        createdAt: plan.created_at
    }));
}

// Subscribe to a reading plan
async function subscribeToReadingPlan(planId, startDate) {
    const user = await getUser();
    if (!user) throw new Error('Not authenticated');

    const { data, error } = await supabaseClient
        .from('user_reading_plans')
        .upsert({
            user_id: user.id,
            plan_id: planId,
            start_date: startDate,
            is_active: true
        }, { onConflict: 'user_id,plan_id' })
        .select()
        .single();

    if (error) throw error;

    return {
        id: data.id,
        planId: data.plan_id,
        startDate: data.start_date,
        isActive: data.is_active
    };
}

// Unsubscribe from a reading plan (soft delete - sets is_active to false)
async function unsubscribeFromReadingPlan(planId) {
    const user = await getUser();
    if (!user) throw new Error('Not authenticated');

    const { error } = await supabaseClient
        .from('user_reading_plans')
        .update({ is_active: false })
        .eq('user_id', user.id)
        .eq('plan_id', planId);

    if (error) throw error;
}

// Fetch progress for a specific plan
async function fetchPlanProgress(userPlanId) {
    const user = await getUser();
    if (!user) return [];

    const { data, error } = await supabaseClient
        .from('reading_plan_progress')
        .select('day_number, completed_at')
        .eq('user_plan_id', userPlanId);

    if (error) throw error;

    return data.map(p => p.day_number);
}

// Fetch all progress for all user's plans
async function fetchAllPlanProgress() {
    const user = await getUser();
    if (!user) return {};

    // First get user's plan IDs
    const { data: plans, error: plansError } = await supabaseClient
        .from('user_reading_plans')
        .select('id, plan_id')
        .eq('user_id', user.id);

    if (plansError) throw plansError;

    // Create mapping of plan_id -> user_plan_id
    const planIdMap = {};
    for (const plan of plans) {
        planIdMap[plan.plan_id] = plan.id;
    }

    // Fetch all progress
    const { data: progress, error: progressError } = await supabaseClient
        .from('reading_plan_progress')
        .select('user_plan_id, day_number')
        .in('user_plan_id', plans.map(p => p.id));

    if (progressError) throw progressError;

    // Group by plan_id
    const result = {};
    for (const plan of plans) {
        result[plan.plan_id] = {
            userPlanId: plan.id,
            completedDays: []
        };
    }
    for (const p of progress) {
        // Find which plan_id this belongs to
        for (const [planId, userPlanId] of Object.entries(planIdMap)) {
            if (userPlanId === p.user_plan_id) {
                result[planId].completedDays.push(p.day_number);
                break;
            }
        }
    }

    return result;
}

// Mark a day as complete
async function markDayComplete(userPlanId, dayNumber) {
    const user = await getUser();
    if (!user) throw new Error('Not authenticated');

    const { error } = await supabaseClient
        .from('reading_plan_progress')
        .upsert({
            user_plan_id: userPlanId,
            day_number: dayNumber
        }, { onConflict: 'user_plan_id,day_number' });

    if (error) throw error;
}

// Unmark a day as complete
async function unmarkDayComplete(userPlanId, dayNumber) {
    const user = await getUser();
    if (!user) throw new Error('Not authenticated');

    const { error } = await supabaseClient
        .from('reading_plan_progress')
        .delete()
        .eq('user_plan_id', userPlanId)
        .eq('day_number', dayNumber);

    if (error) throw error;
}

// Bulk mark multiple days as complete (for catch-up feature)
async function bulkMarkDaysComplete(userPlanId, dayNumbers) {
    const user = await getUser();
    if (!user) throw new Error('Not authenticated');

    if (!dayNumbers || dayNumbers.length === 0) return;

    const records = dayNumbers.map(day => ({
        user_plan_id: userPlanId,
        day_number: day
    }));

    const { error } = await supabaseClient
        .from('reading_plan_progress')
        .upsert(records, { onConflict: 'user_plan_id,day_number' });

    if (error) throw error;
}

// Sync local plan progress to Supabase (for migration from localStorage)
async function syncLocalPlanProgress(planId, startDate, completedDays) {
    const user = await getUser();
    if (!user) return { synced: false };

    try {
        // First ensure the plan subscription exists
        const planData = await subscribeToReadingPlan(planId, startDate);

        // Then sync all completed days
        if (completedDays && completedDays.length > 0) {
            const records = completedDays.map(day => ({
                user_plan_id: planData.id,
                day_number: day
            }));

            const { error } = await supabaseClient
                .from('reading_plan_progress')
                .upsert(records, { onConflict: 'user_plan_id,day_number' });

            if (error) throw error;
        }

        return { synced: true, userPlanId: planData.id };
    } catch (err) {
        console.error('Failed to sync plan progress:', err);
        return { synced: false, error: err.message };
    }
}

// ========== Bug Report Functions ==========

// Submit a bug report
async function submitBugReport(report) {
    const user = await getUser();
    if (!user) throw new Error('Not authenticated');

    const { data, error } = await supabaseClient
        .from('bug_reports')
        .insert({
            user_id: user.id,
            user_email: user.email,
            category: report.category,
            description: report.description,
            verse_reference: report.verseReference || null,
            translation: report.translation || null,
            accuracy_type: report.accuracyType || null,
            screenshot_path: report.screenshotPath || null,
            current_url: report.currentUrl || window.location.href,
            user_agent: navigator.userAgent
        })
        .select()
        .single();

    if (error) throw error;
    return data;
}

// Upload screenshot to Supabase Storage
async function uploadBugScreenshot(file) {
    const user = await getUser();
    if (!user) throw new Error('Not authenticated');

    const fileExt = file.name.split('.').pop();
    const fileName = `${user.id}/${Date.now()}.${fileExt}`;

    const { data, error } = await supabaseClient
        .storage
        .from('bug-screenshots')
        .upload(fileName, file, {
            cacheControl: '3600',
            upsert: false
        });

    if (error) throw error;
    return data.path;
}

// Fetch user's own bug reports (for viewing history)
async function fetchUserBugReports() {
    const user = await getUser();
    if (!user) return [];

    const { data, error } = await supabaseClient
        .from('bug_reports')
        .select('*')
        .eq('user_id', user.id)
        .order('created_at', { ascending: false });

    if (error) throw error;
    return data;
}

// Export for use in app.js
window.SupabaseAuth = {
    getUser,
    signUp,
    signIn,
    signOut,
    resetPassword,
    fetchUserNotes,
    saveUserNote,
    updateUserNote,
    deleteUserNote,
    syncLocalNotesToSupabase,
    onAuthStateChange,
    // Tag functions
    fetchUserTags,
    createUserTag,
    updateUserTag,
    deleteUserTag,
    addTagToNote,
    removeTagFromNote,
    fetchNoteTagIds,
    fetchAllNoteTags,
    setNoteTagIds,
    // Reading plan functions
    fetchUserReadingPlans,
    subscribeToReadingPlan,
    unsubscribeFromReadingPlan,
    fetchPlanProgress,
    fetchAllPlanProgress,
    markDayComplete,
    unmarkDayComplete,
    bulkMarkDaysComplete,
    syncLocalPlanProgress,
    // Bug report functions
    submitBugReport,
    uploadBugScreenshot,
    fetchUserBugReports
};
