#include <iostream>
using namespace std;

int main(){
    int arr[100],
    n=0,
    ch,
    p,
    x;

    do{
        cout << "\n1. Create Array 2. Display Array 3. Insert Salary 4. Delete Salary 5. Display Highest/Lowest Salary 6. Exit\n"
        cin >> ch;

        switch(ch){
            case 1:
                cin >> n;
                for(int i=0;i<n;i++):
                    cin >> a[i];
            break;

            case 2:
                for(int i=0; i<n; i++):
                    cout << a[i] << "";
            break;

            case 3:
                cin >> p >> x;
                for (int i=n; i>=p; i--):
                    a[i] = a[i-1]
                    a[p-1] = x;
                    n++;
            break;

            case 4:
                cin >> p;
                for(int i=p-1; i<n-1; i++):
                    a[i] = a[i+1];
                    n--;
            break;

            case 5:
                int mx = a[0];
                int mn = a[0];

                for(int i=1; i<n; i++):
                    mx = max(mx,a[i]);
                    mn = min(mn,a[i]);
                    cout >> "Highest = " << mx << "Lowest" << mn;
            break;
        }
    }
    while (ch!=6):
        return 0; 
}
