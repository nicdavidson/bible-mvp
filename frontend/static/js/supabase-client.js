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

// Listen for auth state changes
function onAuthStateChange(callback) {
    return supabaseClient.auth.onAuthStateChange((event, session) => {
        callback(event, session?.user || null);
    });
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
    deleteUserNote,
    syncLocalNotesToSupabase,
    onAuthStateChange
};
