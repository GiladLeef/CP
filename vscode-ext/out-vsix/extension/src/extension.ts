import * as vscode from 'vscode';

export function activate(context: vscode.ExtensionContext) {
    const provider = vscode.languages.registerCompletionItemProvider(
        { language: 'c+', scheme: 'file' },
        {
            provideCompletionItems(document, position) {
                const completionItems: vscode.CompletionItem[] = [];

                const f_print = new vscode.CompletionItem('print', vscode.CompletionItemKind.Function);
                f_print.detail = 'A declaration of printf';
                f_print.insertText = new vscode.SnippetString('print("$1");');
                completionItems.push(f_print);

                const f_write = new vscode.CompletionItem('write', vscode.CompletionItemKind.Function);
                f_write.detail = 'A declaration of write';
                f_write.insertText = new vscode.SnippetString('write($1, "$2", $3);');
                completionItems.push(f_write);

                const f_exit = new vscode.CompletionItem('exit', vscode.CompletionItemKind.Function);
                f_exit.detail = 'A declaration of exit';
                f_exit.insertText = new vscode.SnippetString('exit($1);');
                completionItems.push(f_exit);

                const f_fork = new vscode.CompletionItem('fork', vscode.CompletionItemKind.Function);
                f_fork.detail = 'A declaration of fork';
                f_fork.insertText = new vscode.SnippetString('fork();');
                completionItems.push(f_fork);

                const f_execve = new vscode.CompletionItem('execve', vscode.CompletionItemKind.Function);
                f_execve.detail = 'A declaration of execve';
                f_execve.insertText = new vscode.SnippetString('execve("$1", $2, $3);');
                completionItems.push(f_execve);

                const f_malloc = new vscode.CompletionItem('malloc', vscode.CompletionItemKind.Function);
                f_malloc.detail = 'A declaration of malloc';
                f_malloc.insertText = new vscode.SnippetString('malloc($1);');
                completionItems.push(f_malloc);

                /*const f_free = new vscode.CompletionItem('free', vscode.CompletionItemKind.Function);
                f_print.detail = 'A declaration of free';
                f_print.insertText = new vscode.SnippetString('free($1);');
                completionItems.push(f_print);*/

                
                

                return completionItems;
            }
        },
    );

    context.subscriptions.push(provider);
}
