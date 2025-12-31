<?php
/**
 * Create a Firefly III user with owner permissions and generate an API token.
 * This script creates a properly initialized user with full permissions.
 */

require __DIR__ . '/vendor/autoload.php';
$app = require_once __DIR__ . '/bootstrap/app.php';
$kernel = $app->make(Illuminate\Contracts\Console\Kernel::class);
$kernel->bootstrap();

use FireflyIII\User;
use FireflyIII\Models\UserGroup;
use FireflyIII\Models\GroupMembership;
use Illuminate\Support\Facades\Hash;

try {
    $email = 'test@example.com';
    $password = 'password123';

    $user = User::where('email', $email)->first();
    if (!$user) {
        // Create user group first
        $group = new UserGroup();
        $group->title = 'Test User Group';
        $group->save();

        // Create user
        $user = new User();
        $user->email = $email;
        $user->password = Hash::make($password);
        $user->blocked = false;
        $user->blocked_code = null;
        $user->user_group_id = $group->id;
        $user->save();

        // Create group membership with owner role
        $membership = new GroupMembership();
        $membership->user_id = $user->id;
        $membership->user_group_id = $group->id;
        $membership->user_role_id = 21; // 21 = owner role (full permissions including purge)
        $membership->save();
    }

    $token = $user->createToken('Test Token');
    echo "TOKEN=" . $token->accessToken . "\n";
} catch (Exception $e) {
    echo "ERROR: " . $e->getMessage() . "\n";
    exit(1);
}
