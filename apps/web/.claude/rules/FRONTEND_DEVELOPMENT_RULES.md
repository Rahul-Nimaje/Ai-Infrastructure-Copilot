# Frontend Development Rules & Best Practices

This document outlines the mandatory frontend engineering standards, architectural principles, and coding conventions for all frontend applications across all current and future projects.

---

## 1. General Development Rules

- **Think Logic First**: Before doing any task, think through the logic carefully and proceed.
- Write clean, fully optimized, scalable, maintainable, and readable code.
- Follow the existing project architecture and coding conventions.
- Avoid duplicate code and unnecessary complexity.
- Use meaningful and consistent naming conventions.
- Remove unused imports, variables, functions, and dependencies.
- Avoid hardcoded values. Use constants, enums, configuration, or object mappings.
- Use proper TypeScript types and interfaces.
- Avoid `any` unless absolutely necessary.
- Handle loading, error, empty, and success states properly.
- Follow the Single Responsibility Principle.
- Keep components and functions small and focused.

---

## 2. Page and Component Architecture

- Pages should primarily handle routing, layout, permissions, and component composition.
- Do not write large business or UI logic directly inside page files.
- Move business logic into reusable components, hooks, services, or utilities.
- Components should be responsible for their own UI-related logic.
- Create reusable components whenever the same functionality is used in multiple places.
- Avoid duplicating API, validation, formatting, or business logic.

### Recommended Structure

```text
src/
├── components/
│   ├── common/
│   └── feature/
├── hooks/
├── services/
├── utils/
├── constants/
├── types/
└── pages/
```

---

## 3. Object Mapping Instead of switch / Nested if-else

Prefer **Object Mapping** over large switch statements or deeply nested `if/else` conditions. Use mapping/configuration objects, enums, or strategy functions where applicable.

### Preferred
```typescript
const statusConfig = {
  active: {
    label: "Active",
    action: handleActive,
  },
  inactive: {
    label: "Inactive",
    action: handleInactive,
  },
};

statusConfig[status]?.action();
```

### Avoid
```typescript
if (status === "active") {
  handleActive();
} else if (status === "inactive") {
  handleInactive();
}
```

---

## 4. Reusable Components

Create reusable components for commonly used functionality:

- `DataTable`
- `SearchInput`
- `Pagination`
- `AsyncSelect`
- `DatePicker`
- `Modal`
- `ConfirmationDialog`
- `EmptyState`
- `ErrorState`
- `LoadingState`
- `FileUpload`
- `FormField`
- `StatusBadge`

**Rule**: Before creating a new component, check whether an existing reusable component can be extended or reused.

---

## 5. Confirmation Modal for Critical/Destructive Actions

Any button or action that changes or removes data in a way that is destructive, irreversible, or has significant side effects **MUST** trigger a `ConfirmationDialog` (or equivalent confirmation modal) before the action executes. Do not perform the action directly on click.

### Actions That Require Confirmation
- Delete / Remove (single item or bulk delete)
- Update Status (e.g., Active ↔ Inactive, Approve/Reject, Enable/Disable, Publish/Unpublish, Archive/Restore)
- Cancel (e.g., cancel order, cancel subscription)
- Logout / Session termination
- Discard unsaved changes
- Any bulk action affecting multiple records
- Any action that is irreversible or costly to undo

### Rules
- Clicking the action button opens a confirmation modal; it must **never** fire the mutation directly.
- The modal must clearly state what will happen (e.g., "This will permanently delete the selected user. This action cannot be undone.").
- The modal must show the item/record name or count being affected when applicable (e.g., "Delete 3 selected items?").
- Use distinct, clear button labels (e.g., "Delete", "Deactivate") instead of generic "OK"/"Yes" on the confirm button.
- The confirm button should show a loading state while the mutation is in progress and be disabled to prevent duplicate submissions.
- Close the modal and show a success/error toast/notification after the action completes.
- Use a single shared `ConfirmationDialog` component across the app; do not implement one-off confirmation modals per feature.
- Low-risk, easily reversible actions (e.g., opening a filter panel, toggling a UI-only preference) do **not** require confirmation.

### Example
```typescript
const [isConfirmOpen, setIsConfirmOpen] = useState(false);

const handleDeleteClick = () => setIsConfirmOpen(true);

const handleConfirmDelete = async () => {
  await deleteUserMutation.mutateAsync(userId);
  setIsConfirmOpen(false);
};

<ConfirmationDialog
  open={isConfirmOpen}
  title="Delete User"
  description="This will permanently delete this user. This action cannot be undone."
  confirmLabel="Delete"
  isLoading={deleteUserMutation.isPending}
  onConfirm={handleConfirmDelete}
  onCancel={() => setIsConfirmOpen(false)}
/>
```

---

## 6. Reusable Hooks

Extract reusable logic into custom hooks:

- `usePagination`
- `useDebounce`
- `useInfiniteScroll`
- `useFetch`
- `useSearch`
- `useModal`
- `useForm`
- `usePermissions`

**Rule**: Do not duplicate the same state-management or API logic across multiple components.

---

## 7. Reusable Functions and Utilities

Create centralized utility functions for common functionality:

- `formatDate`
- `formatDateTime`
- `formatNumber`
- `formatCurrency`
- `formatPhoneNumber`
- `capitalizeText`
- `truncateText`
- `debounce`
- `buildQueryParams`
- `parseQueryParams`
- `getInitials`

### Rules
- Create common functions once.
- Reuse them throughout the application.
- Do not create duplicate date, number, phone, or string formatting logic.
- Keep utilities pure wherever possible.

---

## 8. Default Required Functions

Common functionality must have a default reusable implementation. At minimum, provide utilities for:

- Date formatting (`formatDate(date)`)
- Date/time formatting (`formatDateTime(date)`)
- Currency formatting (`formatCurrency(amount)`)
- Number formatting (`formatNumber(value)`)
- Phone number formatting (`formatPhoneNumber(phone)`)
- Email validation
- Phone validation
- URL validation
- String formatting
- Debouncing
- Pagination
- Query parameter generation

---

## 9. Forms and Field Types

Identify the correct field type before implementing a form field. Use appropriate input types:

| Field | Input Type |
|---|---|
| Email | `email` |
| Phone | `tel` |
| Password | `password` |
| URL | `url` |
| Date | `date` |
| Number | `number` |
| Text | `text` |

### Rules
- Use `required` for mandatory fields.
- Apply proper validation based on the field type.
- Show meaningful validation messages.
- Do not rely only on frontend validation.
- Frontend validation should match backend validation.

---

## 10. Validation Rules

### Field Types & Rules Overview
Always identify whether a field is: **Required**, **Optional**, **Email**, **Phone**, **Number**, **URL**, **Date**, **Boolean**, **Enum**, **File**, or **Password**.

### Code Examples

- **Email**:
  ```typescript
  email: {
    required: true,
    type: "email"
  }
  ```
- **Phone**:
  ```typescript
  phone: {
    required: true,
    type: "tel"
  }
  ```
- **Number**:
  ```typescript
  amount: {
    required: true,
    type: "number",
    min: 0
  }
  ```
- **URL**:
  ```typescript
  website: {
    required: false,
    type: "url"
  }
  ```

---

## 11. Memoization

Use memoization where it improves performance:

- `useMemo` for expensive calculations.
- `useCallback` for functions passed to memoized child components.
- `React.memo` for components where it prevents unnecessary re-renders.

### Example
```typescript
const filteredUsers = useMemo(() => {
  return users.filter(
    (user) => user.status === selectedStatus
  );
}, [users, selectedStatus]);
```

### Rules
- Avoid unnecessary re-renders.
- Avoid unnecessary API calls.
- Do not use memoization for trivial calculations without a performance benefit.
- Analyze dependencies carefully to avoid stale values.

---

## 12. Fetch-All APIs and Pagination

The frontend **MUST** pass pagination parameters to every fetch-all/list API.

### Standard Request
```typescript
getUsers({
  page: 1,
  limit: 20,
});
```

### With Search & Filters
```typescript
getUsers({
  page: 1,
  limit: 20,
  search: searchTerm,
});
```

### Rules
- Always pass `page`.
- Always pass `limit`.
- Pass `search` parameters when applicable.
- Pass filter parameters when applicable.
- Pass sorting parameters when applicable.
- Reset `page` to `1` when search/filter changes.
- Do not fetch all records unless explicitly required.
- Use reusable pagination logic.

---

## 13. Select / Dropdown API Rules

All API-driven selects with potentially large datasets **MUST** support:

- Search box
- Debounced search
- API pagination
- Infinite scroll
- Loading state
- Duplicate request prevention
- Pagination reset when search changes
- Append new results
- Stop requesting when no more data exists

### Required Flow
```text
Open Select
    ↓
Fetch Page 1
    ↓
User Searches
    ↓
Debounce Search
    ↓
Reset Page = 1
    ↓
Fetch Results
    ↓
User Scrolls to Bottom
    ↓
Fetch Next Page
    ↓
Append Results
    ↓
Stop When No More Data
```

### Example Code
```typescript
const loadOptions = async ({
  search,
  page,
}: {
  search: string;
  page: number;
}) => {
  return getUsers({
    search,
    page,
    limit: 20,
  });
};
```

Create a reusable component such as `AsyncSelect`. **Do not** create separate implementations of searchable/paginated selects for every page.

---

## 14. API Calls & Server State (TanStack Query / React Query)

- **Use TanStack Query / React Query**: Use TanStack Query (`useQuery`, `useMutation`, `useInfiniteQuery`) for all API data fetching, server state caching, background synchronization, and deduplication.
- **Server State Separation**: Do not manually store API response data in local `useState` or global client stores (`Zustand`/`Redux`) when TanStack Query already handles caching and state lifecycle.
- **Centralized Query Keys**: Use structured, centralized query key factories or constants (e.g., `queryKeys.brands.detail(id)`) to ensure consistent cache invalidation.
- **Cache Invalidation**: Always invalidate or update relevant queries using `queryClient.invalidateQueries({ queryKey })` after successful mutations.
- **Keep API Calls in Service Modules**: Define raw API requests inside dedicated service/API modules. Pass clean request functions to `useQuery` / `useMutation`.
- **Proper State Handling**: Explicitly handle query states (`isLoading`, `isFetching`, `isError`, `error`, `data`) and render appropriate UI fallbacks.
- **Prevent Duplicate Requests**: Rely on React Query's default deduplication and stale-time configs. Cancel or ignore stale requests where appropriate.

---

## 15. State Management (Zustand / Redux)

- **Global Client UI State**: Use **Zustand** (or **Redux**) strictly for global client-only application UI state (e.g., auth session/token metadata, theme preferences, sidebar/navigation state, active global modals).
- **Keep Local UI State Local**: Use React `useState` / `useReducer` for state that is isolated to a single component or form.
- **Use Selectors**: Always use atomic selectors (e.g., `useAppStore(state => state.isSidebarOpen)`) instead of extracting the entire store object, to prevent unnecessary re-renders.
- **Avoid Unnecessary Global State**: Do not push state into Zustand/Redux unless it is genuinely shared across multiple non-hierarchical routes/components.
- **Keep API & Server State Separate**: Never copy server API data into Zustand/Redux stores unless performing offline mutations or explicit client-side caching beyond query lifecycle.
- **Avoid Direct State Mutations**: Always update store state immutably using set functions or Immer.

---

## 16. Performance Optimization

- Avoid unnecessary API calls.
- Avoid unnecessary component renders.
- Use pagination for large datasets.
- Use lazy loading for heavy components.
- Use virtualization for very large lists/tables where appropriate.
- Debounce search inputs.
- Memoize expensive calculations.
- Avoid creating unnecessary objects/functions during render.
- Optimize images and assets.
- Avoid loading unnecessary data.

---

## 17. Final FE Checklist

- [ ] Code is optimized and maintainable.
- [ ] Page files do not contain unnecessary business logic.
- [ ] Reusable components are created.
- [ ] Delete/status-change/bulk/irreversible actions use a `ConfirmationDialog` before executing.
- [ ] Reusable hooks are created.
- [ ] Reusable functions/utilities are created.
- [ ] Object Mapping is preferred over switch/nested if-else.
- [ ] Default date/number/phone formatting functions are available.
- [ ] Correct field types are used.
- [ ] Required fields have required validation.
- [ ] Email fields use email validation.
- [ ] Phone fields use phone validation.
- [ ] Memoization is used where beneficial.
- [ ] Fetch-all APIs receive pagination parameters.
- [ ] Select components have search.
- [ ] Select components support API pagination.
- [ ] Select components support infinite scroll.
- [ ] Search requests are debounced.
- [ ] Loading/error/empty states are handled.
- [ ] TanStack Query / React Query is used for API fetching, caching, and server state.
- [ ] Query keys are defined systematically and invalidated after mutations.
- [ ] Zustand or Redux is used strictly for global client UI state.
- [ ] Selectors are used with Zustand/Redux to prevent unnecessary re-renders.
- [ ] Feature routes are protected with localized Error Boundaries.
- [ ] In-flight requests are aborted using AbortController to prevent race conditions.
- [ ] No duplicate API or business logic exists.
- [ ] No unnecessary API calls or re-renders exist.

---

## 18. Senior Architect Guidelines (20+ Years Experience Standards)

1. **Defensive Error Boundaries & Isolation**:
   - Wrap feature routes and critical component sub-trees in localized **React Error Boundaries**. A single failing widget must never crash the entire page. Provide graceful fallback interfaces with retry actions.

2. **Race Condition Prevention & Request Cancellation**:
   - Always handle component unmounting and query key changes properly. Use `AbortController` (or React Query's built-in signal) to cancel in-flight network requests when search queries change or components unmount, eliminating state corruption from race conditions.

3. **Zero-Trust Client Security**:
   - Never store sensitive authentication tokens (e.g. refresh tokens, private keys) in `localStorage` or `sessionStorage` where XSS can extract them. Prefer `httpOnly`, `Secure`, `SameSite` cookies.
   - Always sanitize dynamically rendered HTML, SVG, or Markdown content using `DOMPurify` or `sanitize-html`.

4. **Client Observability & Real User Monitoring (RUM)**:
   - Integrate centralized client error logging (e.g., Sentry) to capture unhandled promise rejections and boundary crashes.
   - Continuously monitor Core Web Vitals (LCP, FID/INP, CLS) to enforce real-world performance budgets.

5. **Architectural Feature Boundaries (No Circular Imports)**:
   - Enforce strict module boundaries. Components in `feature-A` must never directly import internal private implementations from `feature-B`. Shared code must be explicitly promoted to `@/components/common`, `@/hooks`, or `@/utils`.

6. **Graceful Network Resilience & Offline Awareness**:
   - Design interfaces to handle network latency, offline transitions, and intermittent connectivity cleanly. Display contextual retry triggers instead of generic white-screen crashes.
